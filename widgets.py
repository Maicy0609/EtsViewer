"""
自定义控件模块
包含CenteredStaticText、TSListView、ContentJsonViewer
"""
import re
import json
import wx
from os import walk
from datetime import datetime
from os.path import getmtime, join as path_join

from utils import MAX_SIZE, get_font
from formatters import format_question_json


class CenteredStaticText(wx.StaticText):
    """居中显示的静态文本控件"""
    
    def __init__(self, parent, id=wx.ID_ANY, label=wx.EmptyString, 
                 pos=wx.DefaultPosition, size=wx.DefaultSize, 
                 style=0, name=wx.StaticTextNameStr):
        super().__init__(parent, id, label, pos, size, style, name)
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, event: wx.PaintEvent):
        dc = wx.PaintDC(self)
        label = self.GetLabel()
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        dc.SetFont(self.GetFont())
        text_size = dc.GetTextExtent(label)
        size = self.GetSize()
        dc.DrawText(label, (size[0] - text_size[0]) // 2, (size[1] - text_size[1]) // 2)


class TSListView(wx.ListCtrl):
    """题目文件夹列表视图"""
    
    def __init__(self, parent: wx.Window, on_item_selected_callback):
        super().__init__(parent, size=(250, MAX_SIZE[1]), 
                        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_SORT_ASCENDING)
        self._callback = on_item_selected_callback
        self.root_dir = ""
        
        self.InsertColumn(0, "文件名", width=60)
        self.InsertColumn(1, "更改时间", width=140)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)

    def load_dir(self, dir_path: str):
        """加载目录内容"""
        self.root_dir = dir_path
        walk_obj = walk(dir_path)
        _, dir_names, _ = next(walk_obj)
        self.DeleteAllItems()
        
        full_number_pattern = re.compile(r".*\d+")
        for dir_name in dir_names:
            if not re.match(full_number_pattern, dir_name):
                continue
            self.InsertItem(self.GetItemCount(), dir_name)
            mtime = getmtime(path_join(dir_path, dir_name))
            mtime_string = datetime.fromtimestamp(int(mtime))
            self.SetItem(self.GetItemCount() - 1, 1, str(mtime_string))
            self.SetItemData(self.GetItemCount() - 1, int(mtime * 100))
        
        self.SortItems(self._sort_callback)

    def _sort_callback(self, item1, item2):
        return item2 - item1

    def _on_item_selected(self, event: wx.ListEvent):
        item: wx.ListItem = event.GetItem()
        self._callback(item.GetText())


class ContentJsonViewer(wx.Panel):
    """JSON内容查看器面板"""
    
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.activate_exam_dir = ""
        self.contents = []
        self.content_names = []
        self.content_index = 0
        self.ctrl_down = False
        self.pretty_print_enabled = True
        self.show_full_answers = False
        
        self._init_ui()

    def _init_ui(self):
        """初始化UI组件"""
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 选项栏
        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pretty_print_checkbox = wx.CheckBox(self, label="启用美观输出")
        self.pretty_print_checkbox.SetValue(True)
        self.pretty_print_checkbox.Bind(wx.EVT_CHECKBOX, self._on_pretty_print_toggle)
        
        self.full_answers_checkbox = wx.CheckBox(self, label="显示完整答案")
        self.full_answers_checkbox.SetValue(False)
        self.full_answers_checkbox.Bind(wx.EVT_CHECKBOX, self._on_full_answers_toggle)
        
        self.export_btn = wx.Button(self, label="导出为TXT")
        self.export_btn.Bind(wx.EVT_BUTTON, self._export_to_txt)
        
        option_sizer.Add(self.pretty_print_checkbox, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        option_sizer.Add(self.full_answers_checkbox, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        option_sizer.Add(self.export_btn, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        sizer.Add(option_sizer, proportion=0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)

        # 导航栏
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self, label="返回")
        self.forward_btn = wx.Button(self, label="前进")
        self.content_dir_text = CenteredStaticText(self, label="当前目录：")
        self.content_dir_text.SetMinSize((MAX_SIZE[0], -1))
        
        top_sizer.Add(self.back_btn, proportion=0)
        top_sizer.Add(self.content_dir_text, flag=wx.EXPAND, proportion=1)
        top_sizer.Add(self.forward_btn, proportion=0)
        sizer.Add(top_sizer, proportion=0)

        # 内容显示区
        self.json_viewer = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.json_viewer, flag=wx.EXPAND, proportion=1)

        self.SetSizer(sizer)
        self.font_size = self.json_viewer.GetFont().GetPointSize()

        # 绑定事件
        self.back_btn.Bind(wx.EVT_BUTTON, self._prev_content)
        self.forward_btn.Bind(wx.EVT_BUTTON, self._next_content)
        self.content_dir_text.Bind(wx.EVT_LEFT_DOWN, self._popup_choose_menu)
        self.json_viewer.Bind(wx.EVT_KEY_DOWN, lambda e: self._on_key_down(e, True))
        self.json_viewer.Bind(wx.EVT_KEY_UP, lambda e: self._on_key_down(e, False))
        self.json_viewer.Bind(wx.EVT_MOUSEWHEEL, self._on_scroll)

    def _on_pretty_print_toggle(self, event: wx.CommandEvent):
        self.pretty_print_enabled = event.IsChecked()
        self.full_answers_checkbox.Enable(event.IsChecked())
        if self.contents:
            self._content_change()

    def _on_full_answers_toggle(self, event: wx.CommandEvent):
        self.show_full_answers = event.IsChecked()
        if self.contents and self.pretty_print_enabled:
            self._content_change()

    def _on_key_down(self, event: wx.KeyEvent, down_up: bool):
        if event.GetKeyCode() == wx.WXK_CONTROL:
            self.ctrl_down = down_up
        if not down_up:
            event.Skip()
            return
        elif event.GetKeyCode() == wx.WXK_LEFT and self.ctrl_down:
            self._prev_content()
        elif event.GetKeyCode() == wx.WXK_RIGHT and self.ctrl_down:
            self._next_content()
        else:
            event.Skip()

    def _on_scroll(self, event: wx.MouseEvent):
        if self.ctrl_down:
            if event.GetWheelRotation() > 0:
                self.font_size += 1
            else:
                self.font_size -= 1
            self.json_viewer.SetFont(get_font(self.font_size))
        event.Skip()

    def _popup_choose_menu(self, _):
        if self.activate_exam_dir == "":
            return
        menu = wx.Menu()
        for i, content_name in enumerate(self.content_names):
            menu.Append(i, content_name)
            menu.Bind(wx.EVT_MENU, self._switch_to_item, id=i)
        menu.Enable(self.content_index, False)
        self.content_dir_text.PopupMenu(menu)

    def _switch_to_item(self, event: wx.MenuEvent):
        self.content_index = event.GetId()
        self._content_change()

    def _next_content(self, *_):
        self.content_index += 1
        if self._check_index():
            self._content_change()
        else:
            self.content_index -= 1
            wx.MessageBox("已经是最后一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def _prev_content(self, *_):
        self.content_index -= 1
        if self._check_index():
            self._content_change()
        else:
            self.content_index += 1
            wx.MessageBox("已经是第一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def _check_index(self) -> bool:
        return 0 <= self.content_index < len(self.contents)

    def _content_change(self):
        self.content_dir_text.SetLabel(f"当前目录：{self.content_names[self.content_index]}")
        self.GetSizer().Layout()
        
        if self.pretty_print_enabled:
            formatted_content = format_question_json(
                self.contents[self.content_index],
                show_full_answers=self.show_full_answers
            )
        else:
            formatted_content = json.dumps(self.contents[self.content_index], indent=4, ensure_ascii=False)
        self.json_viewer.SetValue(formatted_content)

    def init_data(self, dir_path: str):
        """初始化数据，加载目录中的content.json文件"""
        self.content_names.clear()
        self.contents.clear()
        self.activate_exam_dir = dir_path
        
        walk_obj = walk(dir_path)
        _, dir_names, _ = next(walk_obj)
        errors = []
        
        for dir_name in dir_names:
            if dir_name.startswith("content"):
                try:
                    with open(path_join(dir_path, dir_name, "content.json"), "r", encoding="utf-8") as f:
                        content_text = f.read()
                    self.contents.append(json.loads(content_text))
                    self.content_names.append(dir_name)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    errors.append(f"{dir_name}: {str(e)}")
        
        if errors:
            wx.MessageBox(f"解析错误：\n" + "\n".join(errors), "错误", wx.OK | wx.ICON_ERROR, parent=self)
        
        self.content_index = 0
        self._content_change()

    def _export_to_txt(self, event: wx.CommandEvent):
        """导出内容为TXT文件"""
        if not self.contents or not self.activate_exam_dir:
            wx.MessageBox("没有可导出的数据或目录未加载。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        
        dir_path_parts = self.activate_exam_dir.replace('\\', '/').split('/')
        folder_name = dir_path_parts[-1] if dir_path_parts[-1] else dir_path_parts[-2]
        
        with wx.FileDialog(
            self,
            message="保存导出文件",
            defaultDir="",
            defaultFile=f"export_{folder_name}.txt",
            wildcard="Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            pathname = fileDialog.GetPath()
            try:
                with open(pathname, 'w', encoding='utf-8') as file:
                    for i, (content_name, content_data) in enumerate(zip(self.content_names, self.contents)):
                        file.write(f"--- 条目 {i+1}: {content_name} ---\n")
                        if self.pretty_print_enabled:
                            formatted_content = format_question_json(
                                content_data,
                                show_full_answers=self.show_full_answers
                            )
                        else:
                            formatted_content = json.dumps(content_data, indent=4, ensure_ascii=False)
                        file.write(formatted_content)
                        file.write("\n\n")
                wx.MessageBox(f"导出成功！文件保存至：\n{pathname}", "成功", wx.OK | wx.ICON_INFORMATION)
            except IOError:
                wx.MessageBox(f"无法保存文件：{pathname}", "错误", wx.OK | wx.ICON_ERROR)
