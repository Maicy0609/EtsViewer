"""
ETSViewer - ETS考试内容查看器
主程序入口
"""
import re
import os
import wx
from os.path import join as path_join, expandvars, isdir

from widgets import TSListView, ContentJsonViewer

# 菜单项 ID
_MENU_OPEN_DIR = 0
_MENU_AUTO_DIR = 1
_MENU_RELOAD = 2

# ETS 用户目录名：20 位以上大写十六进制
_ETS_DIR_RE = re.compile(r"[0-9A-F]{20,}")


class Viewer(wx.Frame):
    """主窗口"""

    def __init__(self, parent: wx.Frame | None = None) -> None:
        super().__init__(parent, title="ETSViewer", size=(820, 780))
        self.ts_parent_dir = ""

        # 布局
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ts_list = TSListView(self, self._on_ts_dir_change)
        self.content_json_viewer = ContentJsonViewer(self)
        sizer.Add(self.ts_list, proportion=0)
        sizer.Add(self.content_json_viewer, flag=wx.EXPAND, proportion=1)
        self.SetSizer(sizer)

        # 菜单栏
        self._init_menu()

    def _init_menu(self) -> None:
        """初始化菜单栏"""
        self.menu_bar = wx.MenuBar()
        open_menu = wx.Menu()
        open_menu.Append(_MENU_OPEN_DIR, "打开文件夹")
        open_menu.Append(_MENU_AUTO_DIR, "自动选择文件夹")
        open_menu.Append(_MENU_RELOAD, "刷新文件夹")
        open_menu.Enable(_MENU_RELOAD, False)
        open_menu.Bind(wx.EVT_MENU, self._load_choose_dir, id=_MENU_OPEN_DIR)
        open_menu.Bind(wx.EVT_MENU, self._load_default_dir, id=_MENU_AUTO_DIR)
        open_menu.Bind(wx.EVT_MENU, self._reload, id=_MENU_RELOAD)
        self.menu_bar.Append(open_menu, "操作")
        self.SetMenuBar(self.menu_bar)
        self._open_menu = open_menu

    def _reload(self, *_args: object) -> None:
        """刷新当前目录"""
        if self.ts_parent_dir:
            self._load_dir(self.ts_parent_dir)

    def _on_ts_dir_change(self, dir_name: str) -> None:
        """题目目录变更回调"""
        dir_path = path_join(self.ts_parent_dir, dir_name)
        self.content_json_viewer.init_data(dir_path)

    def _load_default_dir(self, *_args: object) -> None:
        """自动加载默认ETS目录"""
        roaming_dir = expandvars(r"%APPDATA%")
        if not isdir(roaming_dir):
            wx.MessageBox("未找到ETS文件夹", "错误", wx.OK | wx.ICON_ERROR, parent=self)
            return

        try:
            entries = sorted(os.listdir(roaming_dir))
        except OSError:
            entries = []

        for dir_name in entries:
            if _ETS_DIR_RE.match(dir_name) and isdir(path_join(roaming_dir, dir_name)):
                self._load_dir(path_join(roaming_dir, dir_name))
                return

        ets_dir = path_join(roaming_dir, "ETS")
        if isdir(ets_dir):
            self._load_dir(ets_dir)
        else:
            wx.MessageBox("未找到ETS文件夹", "错误", wx.OK | wx.ICON_ERROR, parent=self)

    def _load_choose_dir(self, *_args: object) -> None:
        """手动选择目录"""
        with wx.DirDialog(self, "选择文件夹") as dir_dlg:
            if dir_dlg.ShowModal() == wx.ID_OK:
                self._load_dir(dir_dlg.GetPath())

    def _load_dir(self, dir_path: str) -> None:
        """加载指定目录"""
        if not isdir(dir_path):
            wx.MessageBox(f"目录不存在：\n{dir_path}", "错误",
                          wx.OK | wx.ICON_ERROR, parent=self)
            return
        self._open_menu.Enable(_MENU_RELOAD, True)
        self.ts_parent_dir = dir_path
        self.ts_list.load_dir(dir_path)


def main() -> None:
    app = wx.App()  # type: ignore[no-untyped-call]
    viewer = Viewer(None)
    viewer.Show()
    app.MainLoop()  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    main()
