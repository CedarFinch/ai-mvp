"""通过持久化浏览器登录态采集抖音公开页面。"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any, TYPE_CHECKING
from urllib.parse import quote

from ...common.errors import AIServiceError
from .parser import merge_video, normalize_aweme
from .schemas import DouyinCollectRequest, DouyinCollectResponse, DouyinTargetError, DouyinVideo


_VIDEO_ID_PATTERN = re.compile(r"(?:/video/|[?&](?:modal_id|aweme_id)=)(\d{8,})")
_LOGIN_PROMPTS = ("登录后即可搜索更多精彩视频",)
_RISK_CONTROL_PROMPTS = (
    "请选择所有符合上文描述的图片",
    "拖拽到这里",
    "安全验证",
    "访问过于频繁",
)

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page


class DouyinCollector:
    """串行复用一个浏览器配置目录，避免并发操作同一 Chrome profile。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def collect(self, request: DouyinCollectRequest) -> DouyinCollectResponse:
        if not request.keywords and not request.accounts:
            return DouyinCollectResponse()
        if not self._lock.acquire(blocking=False):
            raise AIServiceError("DOUYIN_COLLECTING", "已有抖音采集任务正在运行", 409)
        try:
            return self._collect_locked(request)
        finally:
            self._lock.release()

    def _collect_locked(self, request: DouyinCollectRequest) -> DouyinCollectResponse:
        videos: dict[str, dict[str, Any]] = {}
        errors: list[DouyinTargetError] = []
        configured_profile_dir = os.getenv("DOUYIN_BROWSER_USER_DATA_DIR", "").strip()
        project_root = Path(__file__).resolve().parents[4]
        profile_dir = Path(configured_profile_dir).expanduser() if configured_profile_dir else Path(".douyin-browser-profile")
        if not profile_dir.is_absolute():
            profile_dir = project_root / profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        headless = os.getenv("DOUYIN_BROWSER_HEADLESS", "false").strip().lower() in {
            "1", "true", "yes", "on"
        }
        channel = os.getenv("DOUYIN_BROWSER_CHANNEL", "chrome").strip()
        timeout = int(os.getenv("DOUYIN_PAGE_TIMEOUT_MILLIS", "20000"))

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                launch_options: dict[str, Any] = {"headless": headless}
                if channel:
                    launch_options["channel"] = channel
                context = playwright.chromium.launch_persistent_context(
                    str(profile_dir.resolve()), **launch_options
                )
                context.set_default_timeout(timeout)
                try:
                    authentication_blocked = False
                    for keyword in request.keywords:
                        if not self._collect_target(
                            context, "KEYWORD", keyword,
                            f"https://www.douyin.com/search/{quote(keyword)}?type=video",
                            keyword, request.max_results_per_target, videos, errors,
                        ):
                            authentication_blocked = True
                            break
                        if len(videos) >= request.max_videos:
                            break
                    if not authentication_blocked and len(videos) < request.max_videos:
                        for account_url in request.accounts:
                            if not self._collect_target(
                                context, "ACCOUNT", account_url, account_url, None,
                                request.max_results_per_target, videos, errors,
                            ):
                                break
                            if len(videos) >= request.max_videos:
                                break
                finally:
                    context.close()
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(
                "DOUYIN_BROWSER_FAILED",
                f"抖音浏览器启动或执行失败：{type(exc).__name__}: {exc}",
                502,
            ) from exc

        return DouyinCollectResponse(
            videos=[DouyinVideo.model_validate(row) for row in list(videos.values())[:request.max_videos]],
            errors=errors,
        )

    def _collect_target(
        self,
        context: "BrowserContext",
        target_type: str,
        target_value: str,
        url: str,
        matched_keyword: str | None,
        limit: int,
        videos: dict[str, dict[str, Any]],
        errors: list[DouyinTargetError],
    ) -> bool:
        page = context.new_page()
        network_awemes: list[dict[str, Any]] = []

        def capture_aweme_response(response: Any) -> None:
            """保留搜索接口返回的数据，避免页面 DOM 改版后完全无法采集。"""
            try:
                content_type = response.header_value("content-type") or ""
                response_url = response.url.lower()
                if "json" not in content_type.lower() or not any(
                    marker in response_url for marker in ("aweme", "search", "post")
                ):
                    return
                network_awemes.extend(_find_aweme_objects(response.json()))
            except Exception:
                # 页面会同时请求大量非业务接口，单个响应不可读不应中断整次采集。
                return

        page.on("response", capture_aweme_response)
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            body_text = page.locator("body").inner_text(timeout=3000)
            if _contains_risk_control(body_text):
                raise DouyinRiskControlRequired(
                    "抖音触发图片或频率验证，本轮采集已停止；请人工完成验证后调用手动接口重试"
                )
            if any(prompt in body_text for prompt in _LOGIN_PROMPTS):
                self._wait_for_login(page)
            try:
                page.wait_for_selector(
                    'a[href*="/video/"], a[href*="modal_id="], a[href*="aweme_id="]',
                    timeout=5000,
                )
            except Exception:
                pass
            rows = self._extract_awemes(page, matched_keyword, network_awemes)
            if target_type == "ACCOUNT":
                expected_author = target_value.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
                author_rows = [row for row in rows if row.get("author_sec_user_id")]
                matching_rows = [
                    row for row in author_rows
                    if row.get("author_sec_user_id") == expected_author
                ]
                if matching_rows:
                    rows = matching_rows
                elif author_rows:
                    raise RuntimeError("账号页面没有解析到该作者的视频，可能是登录失效或页面结构变化")
            if not rows:
                body_text = page.locator("body").inner_text(timeout=3000)
                if _contains_risk_control(body_text):
                    raise DouyinRiskControlRequired(
                        "抖音触发图片或频率验证，本轮采集已停止；请人工完成验证后调用手动接口重试"
                    )
                if any(word in body_text for word in ("验证码", "扫码登录", "登录后查看", *_LOGIN_PROMPTS)):
                    raise DouyinAuthenticationRequired("抖音登录未完成或触发验证，请人工登录后重试")
                raise RuntimeError("页面没有解析到视频，可能是页面结构发生变化")
            for row in rows[:limit]:
                video_id = row["douyin_video_id"]
                videos[video_id] = merge_video(videos[video_id], row) if video_id in videos else row
            return True
        except Exception as exc:
            errors.append(DouyinTargetError(
                target_type=target_type, target_value=target_value, message=str(exc)
            ))
            return not isinstance(exc, (DouyinAuthenticationRequired, DouyinRiskControlRequired))
        finally:
            page.close()

    def _wait_for_login(self, page: "Page") -> None:
        """二维码出现后固定停留在当前页，登录成功才继续，不在多个关键词间跳转。"""
        wait_seconds = max(10, int(os.getenv("DOUYIN_LOGIN_WAIT_SECONDS", "120")))
        try:
            page.wait_for_function(
                "prompts => !prompts.some(prompt => document.body.innerText.includes(prompt))",
                arg=list(_LOGIN_PROMPTS),
                timeout=wait_seconds * 1000,
            )
            page.wait_for_timeout(1500)
        except Exception as exc:
            raise DouyinAuthenticationRequired(
                f"等待扫码登录超时（{wait_seconds}秒），本轮采集已停止"
            ) from exc

    def _extract_awemes(
        self,
        page: "Page",
        matched_keyword: str | None,
        network_awemes: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """合并接口、hydration 数据和视频卡片，兼容抖音搜索页结构变化。"""
        anchor_rows = page.eval_on_selector_all(
            'a[href*="/video/"], a[href*="modal_id="], a[href*="aweme_id="]',
            _CARD_EXTRACTOR_SCRIPT,
        )
        visible_video_ids = {
            match.group(1)
            for anchor in anchor_rows
            if (match := _VIDEO_ID_PATTERN.search(anchor.get("href", "")))
        }
        raw_rows = [*(network_awemes or []), *page.evaluate(_AWEME_EXTRACTOR_SCRIPT)]
        rows: dict[str, dict[str, Any]] = {}
        for raw in raw_rows:
            normalized = normalize_aweme(raw, matched_keyword)
            if normalized and (
                not visible_video_ids or normalized["douyin_video_id"] in visible_video_ids
            ):
                rows[normalized["douyin_video_id"]] = normalized

        if rows:
            return list(rows.values())

        for anchor in anchor_rows:
            href = anchor.get("href", "")
            match = _VIDEO_ID_PATTERN.search(href)
            if not match:
                continue
            video_id = match.group(1)
            raw = {
                "aweme_id": video_id,
                "title": anchor.get("title"),
                "desc": anchor.get("description"),
                "author": {"nickname": anchor.get("author_name")},
                "video": {
                    "duration": anchor.get("duration"),
                    "cover": {"url_list": [anchor.get("cover_url")] if anchor.get("cover_url") else []},
                },
                "like_count": anchor.get("like_count"),
            }
            normalized = normalize_aweme(raw, matched_keyword)
            if normalized:
                rows[video_id] = normalized
        return list(rows.values())


def _find_aweme_objects(payload: Any) -> list[dict[str, Any]]:
    """从抖音不同版本的接口响应中递归找出视频对象。"""
    found: list[dict[str, Any]] = []
    stack = [payload]
    visited = 0
    while stack and visited < 150_000:
        value = stack.pop()
        visited += 1
        if isinstance(value, dict):
            video_id = (
                value.get("aweme_id")
                or value.get("awemeId")
                or value.get("video_id")
                or value.get("videoId")
                or value.get("item_id")
                or value.get("itemId")
            )
            if video_id and any(key in value for key in ("desc", "title", "video", "statistics")):
                found.append(value)
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return found


_CARD_EXTRACTOR_SCRIPT = r"""
elements => elements.map(element => {
  const card = element.closest('.search-result-card') || element.parentElement;
  const cardText = card ? (card.innerText || '') : '';
  const lines = cardText.split(/\n+/).map(value => value.trim()).filter(Boolean);
  const durationPattern = /^(?:\d{1,2}:)?\d{1,2}:\d{2}$/;
  const countPattern = /^\d+(?:\.\d+)?(?:万|亿)?$/;
  const invalidTexts = new Set(['合集', '直播', '置顶']);
  const candidates = card ? Array.from(card.querySelectorAll('div'))
    .filter(node => node.children.length === 0)
    .map(node => (node.innerText || '').replace(/\s+/g, ' ').trim())
    .filter(text => text.length >= 4 && !durationPattern.test(text)
      && !countPattern.test(text) && !invalidTexts.has(text) && !text.startsWith('@')) : [];
  candidates.sort((left, right) => right.length - left.length);
  const description = candidates[0] || '';
  const durationIndex = lines.findIndex(line => durationPattern.test(line));
  const likeCount = durationIndex >= 0 && countPattern.test(lines[durationIndex + 1] || '')
    ? lines[durationIndex + 1] : null;
  const authorLine = lines.find(line => line.startsWith('@')) || '';
  const image = card ? card.querySelector('img[src]') : null;
  return {
    href: element.href || '',
    title: description.split(/[。！？!?]/, 1)[0].trim(),
    description,
    author_name: authorLine.replace(/^@/, '').split(/\s*·\s*/, 1)[0].trim() || null,
    duration: durationIndex >= 0 ? lines[durationIndex] : null,
    like_count: likeCount,
    cover_url: image ? image.src : null
  };
})
"""


_AWEME_EXTRACTOR_SCRIPT = """
() => {
  const roots = [window._ROUTER_DATA, window.__INITIAL_STATE__, window._SSR_DATA]
    .filter(value => value && typeof value === 'object');
  for (const script of document.querySelectorAll(
    'script#RENDER_DATA, script#__NEXT_DATA__, script[type="application/json"]'
  )) {
    const text = (script.textContent || '').trim();
    if (!text) continue;
    for (const candidate of [text, (() => {
      try { return decodeURIComponent(text); } catch (_) { return ''; }
    })()]) {
      if (!candidate) continue;
      try {
        const parsed = JSON.parse(candidate);
        if (parsed && typeof parsed === 'object') roots.push(parsed);
        break;
      } catch (_) {}
    }
  }
  const found = [];
  const seen = new WeakSet();
  let visited = 0;
  const visit = (value, depth) => {
    if (!value || typeof value !== 'object' || depth > 16 || visited > 150000) return;
    if (seen.has(value)) return;
    seen.add(value);
    visited += 1;
    const videoId = value.aweme_id || value.awemeId || value.video_id
      || value.videoId || value.item_id || value.itemId;
    if (videoId && (value.desc !== undefined || value.video || value.statistics)) {
      found.push(value);
    }
    if (Array.isArray(value)) {
      for (const item of value) visit(item, depth + 1);
    } else {
      for (const key of Object.keys(value)) {
        try { visit(value[key], depth + 1); } catch (_) {}
      }
    }
  };
  for (const root of roots) visit(root, 0);
  return found.map(item => ({
    aweme_id: String(item.aweme_id || item.awemeId || item.video_id
      || item.videoId || item.item_id || item.itemId || ''),
    desc: item.desc || item.title || '',
    create_time: item.create_time || item.createTime,
    author: item.author || item.authorInfo || {},
    statistics: item.statistics || item.stats || {},
    video: item.video || {}
  }));
}
"""


class DouyinAuthenticationRequired(RuntimeError):
    """登录未完成时停止整批任务，避免不断打开新的关键词页面。"""


class DouyinRiskControlRequired(RuntimeError):
    """平台出现人工验证时停止整批任务，不尝试自动点击或绕过验证。"""


def _contains_risk_control(body_text: str) -> bool:
    """识别图片验证、拖拽验证和访问频率限制提示。"""
    return any(prompt in body_text for prompt in _RISK_CONTROL_PROMPTS)
