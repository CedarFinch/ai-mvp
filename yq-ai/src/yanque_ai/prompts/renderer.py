"""提示词模板渲染。"""

from __future__ import annotations


def render_prompt(template: str, variables: dict[str, str] | None = None) -> str:
    """只替换约定变量，避免 JSON 示例中的普通花括号被误处理。"""
    content = template
    for key, value in (variables or {}).items():
        content = content.replace("{" + key + "}", value)
    return content
