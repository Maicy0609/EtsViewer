"""
工具函数模块
包含字体缓存、HTML清理、系统相关工具
"""
import re
import html
import wx
from ctypes import windll

# 系统屏幕尺寸
GetSystemMetrics = windll.user32.GetSystemMetrics
MAX_SIZE = (GetSystemMetrics(0), GetSystemMetrics(1))

# 字体缓存
_font_cache = {}


def get_font(size: int) -> wx.Font:
    """获取指定大小的系统字体（带缓存）"""
    if size not in _font_cache:
        system_font: wx.Font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        system_font.SetPointSize(size)
        _font_cache[size] = system_font
    return _font_cache[size]


def clean_html_tags(content: str) -> str:
    """清理HTML标签，返回纯文本"""
    if not content:
        return ""
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"<[^>]*>", "", content)
    content = html.unescape(content)
    content = re.sub(r"\n\s*\n", "\n", content).strip()
    return content
