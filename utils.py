"""
工具函数模块
包含字体缓存、HTML清理、系统相关工具
"""
import re
import html

import wx

# 字号上下限，避免 Ctrl+滚轮 把字号调到 0 或负数导致文字不可见
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 72

# 屏幕尺寸：非 Windows 平台退化为 1080p，保证模块可被导入（便于测试）
try:
    from ctypes import windll

    _get_system_metrics = windll.user32.GetSystemMetrics
    MAX_SIZE: tuple[int, int] = (_get_system_metrics(0), _get_system_metrics(1))
except (ImportError, AttributeError):  # pragma: no cover - 仅非 Windows 触发
    MAX_SIZE = (1920, 1080)

# 字体缓存
_font_cache: dict[int, wx.Font] = {}

# 需要转成换行的块级/换行标签
_BREAK_TAG_RE = re.compile(r"<br\s*/?>|</br\s*>|</p\s*>|<p[^>]*>", re.IGNORECASE)


def get_font(size: int) -> wx.Font:
    """获取指定大小的系统字体（带缓存）"""
    size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
    if size not in _font_cache:
        system_font: wx.Font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        system_font.SetPointSize(size)
        _font_cache[size] = system_font
    return _font_cache[size]


def clean_html_tags(content: object) -> str:
    """清理HTML标签，返回纯文本

    注意：``<p>`` / ``<br>`` / ``</br>`` 会先被转换为换行符，
    否则阅读材料的段落会被拼成一整段。
    """
    if not content:
        return ""
    text = content if isinstance(content, str) else str(content)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = _BREAK_TAG_RE.sub("\n", text)
    text = re.sub(r"<[^>]*>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()
