"""将页面中的 aweme 数据整理成稳定接口字段。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


_DURATION_PATTERN = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$")
_COUNT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)(万|亿)?$")
_NON_TITLE_TEXTS = {"合集", "直播", "置顶"}


def normalize_aweme(raw: dict[str, Any], matched_keyword: str | None = None) -> dict[str, Any] | None:
    video_id = str(
        raw.get("aweme_id")
        or raw.get("awemeId")
        or raw.get("video_id")
        or raw.get("videoId")
        or raw.get("item_id")
        or raw.get("itemId")
        or ""
    ).strip()
    if not video_id:
        return None

    description = _text(raw.get("desc") or raw.get("description"))
    explicit_title = _text(raw.get("title"))
    title = _derive_title(explicit_title or description)
    if not title:
        # DOM 降级解析如果只拿到“03:09”或“合集”，宁可放弃该条视频，也不写脏数据。
        return None

    author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
    statistics = raw.get("statistics") if isinstance(raw.get("statistics"), dict) else {}
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    cover = video.get("cover") if isinstance(video.get("cover"), dict) else {}
    cover_urls = cover.get("url_list") if isinstance(cover.get("url_list"), list) else []
    sec_user_id = _text(
        author.get("sec_uid")
        or author.get("secUid")
        or author.get("sec_user_id")
        or author.get("secUserId")
    )
    create_time = _integer(raw.get("create_time") or raw.get("createTime"))

    return {
        "douyin_video_id": video_id,
        "video_url": f"https://www.douyin.com/video/{video_id}",
        "title": title[:500],
        "description": description or explicit_title,
        "author_sec_user_id": sec_user_id,
        "author_name": _text(author.get("nickname") or author.get("name")),
        "author_url": f"https://www.douyin.com/user/{sec_user_id}" if sec_user_id else None,
        "cover_url": _text(cover_urls[0]) if cover_urls else None,
        "duration_ms": _duration_ms(video.get("duration") or raw.get("duration")),
        "publish_time": datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat()
        if create_time
        else None,
        "matched_keywords": [matched_keyword] if matched_keyword else [],
        "like_count": _count(
            statistics.get("digg_count")
            or statistics.get("diggCount")
            or raw.get("like_count")
            or raw.get("likeCount")
        ),
    }


def merge_video(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """合并不同目标命中的同一视频，保留更完整字段并合并关键词。"""
    merged = dict(existing)
    for key, value in incoming.items():
        if key == "matched_keywords":
            merged[key] = list(dict.fromkeys([*merged.get(key, []), *value]))
        elif value not in (None, "", []):
            merged[key] = value
    return merged


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _integer(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _derive_title(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split()).strip()
    if normalized in _NON_TITLE_TEXTS or _DURATION_PATTERN.fullmatch(normalized):
        return None
    # 抖音没有独立标题字段时，从完整描述的第一句话生成展示标题，描述仍保留全文。
    without_tags = re.split(r"\s+#", normalized, maxsplit=1)[0].strip()
    sentence = re.split(r"(?<=[。！？!?])\s*", without_tags, maxsplit=1)[0].strip()
    return (sentence or without_tags or normalized)[:120]


def _duration_ms(value: Any) -> int | None:
    if isinstance(value, str):
        match = _DURATION_PATTERN.fullmatch(value.strip())
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return (hours * 3600 + minutes * 60 + seconds) * 1000
    return _integer(value)


def _count(value: Any) -> int | None:
    if isinstance(value, str):
        match = _COUNT_PATTERN.fullmatch(value.strip())
        if not match:
            return None
        multiplier = {None: 1, "万": 10_000, "亿": 100_000_000}[match.group(2)]
        return int(float(match.group(1)) * multiplier)
    return _integer(value)
