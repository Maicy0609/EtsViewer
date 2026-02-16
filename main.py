"""
ETSViewer - ETS考试内容查看器
主程序入口
"""
import re
import wx
from os import walk
from os.path import join as path_join, expandvars, isdir

from widgets import TSListView, ContentJsonViewer


class Viewer(wx.Frame):
    """主窗口"""
    
    def __init__(self, parent: wx.Frame):
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

    def _init_menu(self):
        """初始化菜单栏"""
        self.menu_bar = wx.MenuBar()
        open_menu = wx.Menu()
        open_menu.Append(0, "打开文件夹")
        open_menu.Append(1, "自动选择文件夹")
        open_menu.Append(2, "刷新文件夹")
        open_menu.Enable(2, False)
        open_menu.Bind(wx.EVT_MENU, self._load_choose_dir, id=0)
        open_menu.Bind(wx.EVT_MENU, self._load_default_dir, id=1)
        open_menu.Bind(wx.EVT_MENU, self._reload, id=2)
        self.menu_bar.Append(open_menu, "操作")
        self.SetMenuBar(self.menu_bar)
        self._open_menu = open_menu

    def _reload(self, *_) -> None:
        """刷新当前目录"""
        if self.ts_parent_dir:
            self._load_dir(self.ts_parent_dir)

    def _on_ts_dir_change(self, dir_name: str):
        """题目目录变更回调"""
        dir_path = path_join(self.ts_parent_dir, dir_name)
        self.content_json_viewer.init_data(dir_path)

    def _load_default_dir(self, *_):
        """自动加载默认ETS目录"""
        roaming_dir = expandvars(r"%APPDATA%")
        walk_obj = walk(roaming_dir)
        _, dir_names, _ = next(walk_obj)
        
        match_pattern = re.compile(r"[0-9A-F]{20,}")
        for dir_name in dir_names:
            if re.match(match_pattern, dir_name):
                self._load_dir(path_join(roaming_dir, dir_name))
                return
        
        if isdir(path_join(roaming_dir, "ETS")):
            self._load_dir(path_join(roaming_dir, "ETS"))
        else:
            wx.MessageBox("未找到ETS文件夹", "错误", wx.OK | wx.ICON_ERROR, parent=self)

    def _load_choose_dir(self, *_):
        """手动选择目录"""
        with wx.DirDialog(self, "选择文件夹") as dir_dlg:
            if dir_dlg.ShowModal() == wx.ID_OK:
                self._load_dir(dir_dlg.GetPath())

    def _load_dir(self, dir_path: str):
        """加载指定目录"""
        self._open_menu.Enable(2, True)
        self.ts_parent_dir = dir_path
        self.ts_list.load_dir(dir_path)


if __name__ == "__main__":
    app = wx.App()
    viewer = Viewer(None)
    viewer.Show()
    app.MainLoop()
