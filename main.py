import wx
import re
import json
from os import walk
from ctypes import windll
from datetime import datetime
from widget import CenteredStaticText, ft
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

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)

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
        self.ctrl_down = False
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self, label="返回")
        self.forward_btn = wx.Button(self, label="前进")
        self.content_dir_text = CenteredStaticText(self, label="当前目录：")
        self.content_dir_text.SetMinSize((MAX_SIZE[0], -1))
        self.top_sizer.Add(self.back_btn, proportion=0)
        self.top_sizer.Add(self.content_dir_text, flag=wx.EXPAND, proportion=1)
        self.top_sizer.Add(self.forward_btn, proportion=0)
        self.sizer.Add(self.top_sizer, proportion=0)

        self.json_viewer = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.sizer.Add(self.json_viewer, flag=wx.EXPAND, proportion=1)
        self.SetSizer(self.sizer)

        self.font_size = self.json_viewer.GetFont().GetPointSize()
        self.back_btn.Bind(wx.EVT_BUTTON, self.prev_content)
        self.forward_btn.Bind(wx.EVT_BUTTON, self.next_content)
        self.content_dir_text.Bind(wx.EVT_LEFT_DOWN, self.popup_choose_menu)
        self.json_viewer.Bind(wx.EVT_KEY_DOWN, lambda e:self.on_key_down(e, True))
        self.json_viewer.Bind(wx.EVT_KEY_UP, lambda e:self.on_key_down(e, False))
        self.json_viewer.Bind(wx.EVT_MOUSEWHEEL, self.on_scroll)

    def on_key_down(self, event: wx.KeyEvent, down_up: bool):
        if event.GetKeyCode() == wx.WXK_CONTROL:
            self.ctrl_down = down_up
        if not down_up:
            event.Skip()
            return
        elif event.GetKeyCode() == wx.WXK_LEFT and self.ctrl_down:
            self.prev_content()
        elif event.GetKeyCode() == wx.WXK_RIGHT and self.ctrl_down:
            self.next_content()
        else:
            event.Skip()

    def on_scroll(self, event: wx.MouseEvent):
        if self.ctrl_down:
            if event.GetWheelRotation() > 0:
                self.font_size += 1
            else:
                self.font_size -= 1
            print("当前字体大小:", self.font_size)
            self.json_viewer.SetFont(ft(self.font_size))
        event.Skip()

    def popup_choose_menu(self, _):
        if self.activate_exam_dir == "":
            return
        menu = wx.Menu()
        for i, content_name in enumerate(self.content_names):
            menu.Append(i, content_name)
            menu.Bind(wx.EVT_MENU, self.switch_to_item, id=i)
        menu.Enable(self.content_index, False)
        self.content_dir_text.PopupMenu(menu)

    def switch_to_item(self, event: wx.MenuEvent):
        self.content_index = event.GetId()
        self.content_change()

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
        errors = []
        for dir_name in dir_names:
            if dir_name.startswith("content"):
                with open(path_join(dir_path, dir_name, "content.json"), "r", encoding="utf-8") as content_text:
                    content_text = content_text.read()
                try:
                    self.contents.append(json.loads(content_text))
                    self.content_names.append(dir_name)
                    print("找到试题:", dir_name)
                except json.JSONDecodeError:
                    errors.append(dir_name)
        if errors:
            wx.MessageBox(f"解析错误：{','.join(errors)}", "错误", wx.OK | wx.ICON_ERROR, parent=self)

        self.content_index = 0
        self.content_change()


class Viewer(wx.Frame):
    def __init__(self, parent: wx.Frame):
        super().__init__(parent, title="E听说content.json查看器", size=(820, 780))
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
        self.open_menu.Append(2, "刷新文件夹")
        self.open_menu.Enable(2, False)
        self.open_menu.Bind(wx.EVT_MENU, self.load_choose_dir, id=0)
        self.open_menu.Bind(wx.EVT_MENU, self.load_default_dir, id=1)
        self.open_menu.Bind(wx.EVT_MENU, self.reload, id=2)
        self.menu_bar.Append(self.open_menu, "操作")
        self.SetMenuBar(self.menu_bar)

    def reload(self, *_) -> None:
        print("刷新文件夹")
        if self.ts_parent_dir:
            self.load_dir(self.ts_parent_dir)

    def ts_dir_change(self, dir_name: str):
        print("选择作业:", dir_name)
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
        print("加载文件夹:", dir_path)
        self.open_menu.Enable(2, True)
        self.ts_parent_dir = dir_path
        self.ts_list.load_dir(dir_path)


if __name__ == "__main__":
    app = wx.App()
    viewer = Viewer(None)
    viewer.Show()
    app.MainLoop()
