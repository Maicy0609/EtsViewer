import wx


font_cache = {}


def ft(size: int) -> wx.Size:
    if size not in font_cache:
        system_font: wx.Font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        system_font.SetPointSize(size)
        font_cache[size] = system_font
    return font_cache[size]


class CenteredStaticText(wx.StaticText):
    """使得绘制的文字始终保持在控件中央"""

    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        label=wx.EmptyString,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=0,
        name=wx.StaticTextNameStr,
    ):
        super().__init__(parent, id, label, pos, size, style, name)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event: wx.PaintEvent):
        dc = wx.PaintDC(self)
        label = self.GetLabel()
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        dc.SetFont(self.GetFont())
        Tsize = dc.GetTextExtent(label)
        size = self.GetSize()
        dc.DrawText(label, (size[0] - Tsize[0]) // 2, (size[1] - Tsize[1]) // 2)
