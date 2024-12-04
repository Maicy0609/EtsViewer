import json
import wx
import re
from os import walk
from ctypes import windll
from datetime import datetime
from os.path import getmtime, join as path_join, expandvars

GetSystemMetrics = windll.user32.GetSystemMetrics
MAX_SIZE = (GetSystemMetrics(0), GetSystemMetrics(1))


class TSListView(wx.ListCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(
            parent, size=(250, MAX_SIZE[1]), style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_SORT_ASCENDING
        )
        self.InsertColumn(0, "文件名", width=60)
        self.InsertColumn(1, "更改时间", width=140)
        self.root_dir = ""

        self.last_selected = None
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.check_selection, self.timer)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.timer.Start(100)  # 每秒检查一次

    def check_selection(self, *_):
        if self.GetSelectedItemCount() == 1:
            item = self.GetFirstSelected()
            if item != self.last_selected and item != -1:
                self.last_selected = item
                viewer.ts_dir_change(self.GetItemText(item))

    def load_dir(self, dir_path: str):
        self.root_dir = dir_path
        walk_obj = walk(dir_path)
        _, dir_names, _ = next(walk_obj)
        self.DeleteAllItems()
        full_number_pattern = re.compile(r"\d+")
        for dir_name in dir_names:
            if not re.match(full_number_pattern, dir_name):
                continue
            self.InsertItem(self.GetItemCount(), dir_name)
            mtime = getmtime(path_join(dir_path, dir_name))  # 修改时间
            mtime_string = datetime.fromtimestamp(int(mtime))
            self.SetItem(self.GetItemCount() - 1, 1, str(mtime_string))
            self.SetItemData(self.GetItemCount() - 1, int(mtime * 100))
        self.SortItems(self.SortItemCbkFunc)

    def SortItemCbkFunc(self, item1, item2):
        return item2 - item1

    def on_item_selected(self, event: wx.ListEvent):
        item: wx.ListItem = event.GetItem()
        viewer.ts_dir_change(item.GetText())


class ContentJsonViewer(wx.Panel):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.activate_exam_dir = ""
        self.contents = []
        self.content_names = []
        self.content_index = 0
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self, label="返回")
        self.forward_btn = wx.Button(self, label="前进")
        self.content_dir_text = wx.StaticText(self, label="当前目录：")
        self.content_dir_text.SetMinSize((MAX_SIZE[0], -1))
        self.top_sizer.Add(self.back_btn, proportion=0)
        self.top_sizer.Add(self.content_dir_text, flag=wx.EXPAND, proportion=1)
        self.top_sizer.Add(self.forward_btn, proportion=0)
        self.sizer.Add(self.top_sizer, proportion=0)

        self.json_viewer = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.json_viewer, flag=wx.EXPAND, proportion=1)
        self.SetSizer(self.sizer)

        self.back_btn.Bind(wx.EVT_BUTTON, self.prev_content)
        self.forward_btn.Bind(wx.EVT_BUTTON, self.next_content)

    def next_content(self, *_):
        self.content_index += 1
        if self.check_index():
            self.content_change()
        else:
            self.content_index -= 1
            wx.MessageBox("已经是最后一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def prev_content(self, *_):
        self.content_index -= 1
        if self.check_index():
            self.content_change()
        else:
            self.content_index += 1
            wx.MessageBox("已经是第一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def check_index(self) -> bool:
        if self.content_index >= len(self.contents) or self.content_index < 0:
            return False
        return True

    def content_change(self):
        self.content_dir_text.SetLabel(f"当前目录：{self.content_names[self.content_index]}")
        self.top_sizer.Layout()
        self.json_viewer.SetValue(json.dumps(self.contents[self.content_index], indent=4, ensure_ascii=False))
        

    def init_data(self, dir_path: str):
        self.content_names.clear()
        self.contents.clear()
        
        self.activate_exam_dir = dir_path
        walk_obj = walk(dir_path)
        _, dir_names, _ = next(walk_obj)
        for dir_name in dir_names:
            if dir_name.startswith("content"):
                self.content_names.append(dir_name)
                with open(path_join(dir_path, dir_name, "content.json"), "r", encoding="utf-8") as content_text:
                    content_text = content_text.read()
                self.contents.append(json.loads(content_text))

        self.content_index = 0
        self.content_change()


class Viewer(wx.Frame):
    def __init__(self, parent: wx.Frame):
        super().__init__(parent, title="content.json查看器", size=(820, 780))
        self.ts_parent_dir = ""
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ts_list = TSListView(self)
        self.content_json_viewer = ContentJsonViewer(self)
        self.sizer.Add(self.ts_list, proportion=0)
        self.sizer.Add(self.content_json_viewer, flag=wx.EXPAND, proportion=1)
        self.SetSizer(self.sizer)

        self.menu_bar = wx.MenuBar()
        self.open_menu = wx.Menu()
        self.open_menu.Append(0, "打开文件夹")
        self.open_menu.Append(1, "自动选择文件夹")
        self.open_menu.Bind(wx.EVT_MENU, self.load_choose_dir, id=0)
        self.open_menu.Bind(wx.EVT_MENU, self.load_default_dir, id=1)
        self.menu_bar.Append(self.open_menu, "操作")
        self.SetMenuBar(self.menu_bar)

    def ts_dir_change(self, dir_name: str):
        dir_path = path_join(self.ts_parent_dir, dir_name)
        self.content_json_viewer.init_data(dir_path)

    def load_default_dir(self, *_):
        roaming_dir = expandvars(r"%APPDATA%")
        walk_obj = walk(roaming_dir)
        _, dir_names, _ = next(walk_obj)
        match_pattern = re.compile(r"[0-9A-F]{20,}")
        for dir_name in dir_names:
            if re.match(match_pattern, dir_name):
                self.load_dir(path_join(roaming_dir, dir_name))
                return

    def load_choose_dir(self, *_):
        with wx.DirDialog(self, "选择文件夹") as dir_dlg:
            assert isinstance(dir_dlg, wx.DirDialog)
            if dir_dlg.ShowModal() == wx.ID_OK:
                self.load_dir(dir_dlg.GetPath())

    def load_dir(self, dir_path: str):
        self.ts_parent_dir = dir_path
        self.ts_list.load_dir(dir_path)


if __name__ == "__main__":
    app = wx.App()
    viewer = Viewer(None)
    viewer.Show()
    app.MainLoop()
