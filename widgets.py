"""
自定义控件模块
包含CenteredStaticText、TSListView、ContentJsonViewer
"""
import json
import os
import re
import wx
from datetime import datetime
from os.path import isdir, join as path_join
from typing import Any, Callable

from utils import MAX_FONT_SIZE, MAX_SIZE, MIN_FONT_SIZE, get_font
from formatters import format_question_json

# 试题文件夹名：必须包含数字
_DIR_NAME_RE = re.compile(r".*\d+")
# 时间列显示格式
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class CenteredStaticText(wx.StaticText):
    """居中显示的静态文本控件"""

    def __init__(self, parent: wx.Window, id: int = wx.ID_ANY,
                 label: str = wx.EmptyString,
                 pos: wx.Point = wx.DefaultPosition,
                 size: wx.Size = wx.DefaultSize,
                 style: int = 0, name: str = "staticText") -> None:
        super().__init__(parent, id, label, pos, size, style, name)
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, _event: wx.PaintEvent) -> None:
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

    def __init__(self, parent: wx.Window,
                 on_item_selected_callback: Callable[[str], None]) -> None:
        super().__init__(parent, size=(250, MAX_SIZE[1]),
                         style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._callback = on_item_selected_callback
        self.root_dir = ""
        self._rows: list[tuple[str, float]] = []
        # 默认按「更改时间」倒序：最新日期的作业排在最上面
        self._sort_col = 1
        self._sort_desc = True

        self.InsertColumn(0, "文件名", width=60)
        self.InsertColumn(1, "更改时间", width=140)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
        self.Bind(wx.EVT_LIST_COL_CLICK, self._on_col_click)

    def load_dir(self, dir_path: str) -> None:
        """加载目录内容，默认按修改时间倒序排列"""
        self.root_dir = dir_path
        self._rows = []
        if isdir(dir_path):
            with os.scandir(dir_path) as scanner:
                for entry in scanner:
                    if not entry.is_dir() or not _DIR_NAME_RE.match(entry.name):
                        continue
                    try:
                        self._rows.append((entry.name, entry.stat().st_mtime))
                    except OSError:
                        continue
        self._refresh()

    def _refresh(self) -> None:
        """按当前排序状态重建列表"""
        by_time = self._sort_col == 1
        # 时间列用 (mtime, name) 做键，避免同一时间戳下顺序随机
        if by_time:
            rows = sorted(self._rows, key=lambda r: (r[1], r[0]), reverse=self._sort_desc)
        else:
            rows = sorted(self._rows, key=lambda r: r[0], reverse=self._sort_desc)

        self.DeleteAllItems()
        for dir_name, mtime in rows:
            index = self.InsertItem(self.GetItemCount(), dir_name)
            mtime_string = datetime.fromtimestamp(int(mtime)).strftime(_TIME_FORMAT)
            self.SetItem(index, 1, mtime_string)

    def _on_col_click(self, event: wx.ListEvent) -> None:
        col = event.GetColumn()
        if col == self._sort_col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            # 切到时间列时默认新日期靠上，切到文件名时默认 A→Z
            self._sort_desc = col == 1
        self._refresh()

    def _on_item_selected(self, event: wx.ListEvent) -> None:
        item = event.GetItem()
        if item.GetId() != -1:
            self._callback(item.GetText())


class ContentJsonViewer(wx.Panel):
    """JSON内容查看器面板"""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)
        self.activate_exam_dir = ""
        self.contents: list[Any] = []
        self.content_names: list[str] = []
        self.content_index = 0
        self.ctrl_down = False
        self.pretty_print_enabled = True
        self.show_full_answers = False
        self.font_size = 10

        self._init_ui()

    def _init_ui(self) -> None:
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

        option_sizer.Add(self.pretty_print_checkbox, proportion=0,
                         flag=wx.LEFT | wx.RIGHT, border=10)
        option_sizer.Add(self.full_answers_checkbox, proportion=0,
                         flag=wx.LEFT | wx.RIGHT, border=10)
        option_sizer.Add(self.export_btn, proportion=0,
                         flag=wx.LEFT | wx.RIGHT, border=10)
        sizer.Add(option_sizer, proportion=0,
                  flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)

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

    def _on_pretty_print_toggle(self, event: wx.CommandEvent) -> None:
        self.pretty_print_enabled = event.IsChecked()
        self.full_answers_checkbox.Enable(event.IsChecked())
        if self.contents:
            self._content_change()

    def _on_full_answers_toggle(self, event: wx.CommandEvent) -> None:
        self.show_full_answers = event.IsChecked()
        if self.contents and self.pretty_print_enabled:
            self._content_change()

    def _on_key_down(self, event: wx.KeyEvent, down_up: bool) -> None:
        if event.GetKeyCode() == wx.WXK_CONTROL:
            self.ctrl_down = down_up
        if not down_up:
            event.Skip()
            return
        if event.GetKeyCode() == wx.WXK_LEFT and self.ctrl_down:
            self._prev_content()
        elif event.GetKeyCode() == wx.WXK_RIGHT and self.ctrl_down:
            self._next_content()
        else:
            event.Skip()

    def _on_scroll(self, event: wx.MouseEvent) -> None:
        rotation = event.GetWheelRotation()
        if rotation and (event.ControlDown() or self.ctrl_down):
            step = 1 if rotation > 0 else -1
            new_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, self.font_size + step))
            if new_size != self.font_size:
                self.font_size = new_size
                self.json_viewer.SetFont(get_font(self.font_size))
        event.Skip()

    def _popup_choose_menu(self, _event: wx.MouseEvent) -> None:
        if not self.content_names:
            return
        menu = wx.Menu()
        try:
            for i, content_name in enumerate(self.content_names):
                menu.Append(i, content_name)
                menu.Bind(wx.EVT_MENU, self._switch_to_item, id=i)
            menu.Enable(self.content_index, False)
            self.content_dir_text.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _switch_to_item(self, event: wx.CommandEvent) -> None:
        index = event.GetId()
        if 0 <= index < len(self.contents):
            self.content_index = index
            self._content_change()

    def _next_content(self, *_args: object) -> None:
        if not self.contents:
            return
        if self.content_index + 1 < len(self.contents):
            self.content_index += 1
            self._content_change()
        else:
            wx.MessageBox("已经是最后一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def _prev_content(self, *_args: object) -> None:
        if not self.contents:
            return
        if self.content_index > 0:
            self.content_index -= 1
            self._content_change()
        else:
            wx.MessageBox("已经是第一个了", "提示", wx.OK | wx.ICON_INFORMATION)

    def _check_index(self) -> bool:
        return 0 <= self.content_index < len(self.contents)

    def _content_change(self) -> None:
        """刷新右侧显示内容"""
        if not self.contents:
            # 目录里没有可解析的 content.json，清空显示而不是抛 IndexError
            self.content_index = 0
            self.content_dir_text.SetLabel("当前目录：")
            self.json_viewer.SetValue("")
            self.Layout()
            return

        if not self._check_index():
            self.content_index = 0

        self.content_dir_text.SetLabel(f"当前目录：{self.content_names[self.content_index]}")
        self.Layout()

        content = self.contents[self.content_index]
        if self.pretty_print_enabled:
            text = format_question_json(content, show_full_answers=self.show_full_answers)
        else:
            text = json.dumps(content, indent=4, ensure_ascii=False)
        self.json_viewer.SetValue(text)

    def init_data(self, dir_path: str) -> None:
        """初始化数据，加载目录中的content.json文件"""
        self.content_names.clear()
        self.contents.clear()
        self.activate_exam_dir = dir_path
        errors: list[str] = []

        if isdir(dir_path):
            for dir_name in sorted(os.listdir(dir_path)):
                content_dir = path_join(dir_path, dir_name)
                if not dir_name.startswith("content") or not isdir(content_dir):
                    continue
                try:
                    with open(path_join(content_dir, "content.json"), "r",
                              encoding="utf-8") as f:
                        data: Any = json.load(f)
                except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
                    errors.append(f"{dir_name}: {e}")
                    continue
                self.contents.append(data)
                self.content_names.append(dir_name)

        if errors:
            wx.MessageBox("解析错误：\n" + "\n".join(errors), "错误",
                          wx.OK | wx.ICON_ERROR, parent=self)

        self.content_index = 0
        self._content_change()

    def _export_to_txt(self, _event: wx.CommandEvent) -> None:
        """导出内容为TXT文件"""
        if not self.contents or not self.activate_exam_dir:
            wx.MessageBox("没有可导出的数据或目录未加载。", "提示",
                          wx.OK | wx.ICON_INFORMATION)
            return

        # 用 normpath + basename，避免路径带尾部分隔符时文件名变成 export_.txt
        folder_name = os.path.basename(os.path.normpath(self.activate_exam_dir)) or "ETS"

        with wx.FileDialog(
            self,
            message="保存导出文件",
            defaultFile=f"export_{folder_name}.txt",
            wildcard="Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = file_dialog.GetPath()
            try:
                with open(pathname, "w", encoding="utf-8") as file:
                    for i, (content_name, content_data) in enumerate(
                            zip(self.content_names, self.contents)):
                        file.write(f"--- 条目 {i + 1}: {content_name} ---\n")
                        if self.pretty_print_enabled:
                            formatted = format_question_json(
                                content_data,
                                show_full_answers=self.show_full_answers
                            )
                        else:
                            formatted = json.dumps(content_data, indent=4,
                                                   ensure_ascii=False)
                        file.write(formatted)
                        file.write("\n\n")
                wx.MessageBox(f"导出成功！文件保存至：\n{pathname}", "成功",
                              wx.OK | wx.ICON_INFORMATION)
            except OSError:
                wx.MessageBox(f"无法保存文件：{pathname}", "错误", wx.OK | wx.ICON_ERROR)
