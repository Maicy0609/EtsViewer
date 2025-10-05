import wx
import re
import json
from os import walk
from ctypes import windll
from datetime import datetime
from os.path import getmtime, join as path_join, expandvars, isdir

font_cache = {}

def ft(size: int) -> wx.Font:
    if size not in font_cache:
        system_font: wx.Font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        system_font.SetPointSize(size)
        font_cache[size] = system_font
    return font_cache[size]

class CenteredStaticText(wx.StaticText):
    def __init__(self, parent, id=wx.ID_ANY, label=wx.EmptyString, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, name=wx.StaticTextNameStr):
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

class TSListView(wx.ListCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=(250, MAX_SIZE[1]), style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_SORT_ASCENDING)
        self.InsertColumn(0, "文件名", width=60)
        self.InsertColumn(1, "更改时间", width=140)
        self.root_dir = ""
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)

    def load_dir(self, dir_path: str):
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
        self.SortItems(self.SortItemCbkFunc)

    def SortItemCbkFunc(self, item1, item2):
        return item2 - item1

    def on_item_selected(self, event: wx.ListEvent):
        item: wx.ListItem = event.GetItem()
        viewer.ts_dir_change(item.GetText())

import re
import html

def clean_html_tags(content: str) -> str:
    if not content:
        return ""
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"<[^>]*>", "", content)
    content = html.unescape(content)
    content = re.sub(r"\n\s*\n", "\n", content).strip()
    return content

def format_question_json(json_data, show_full_answers=True):
    structure_type = json_data.get("structure_type")
    if structure_type == "collector.role":
        return format_role_type(json_data, show_full_answers)
    elif structure_type == "collector.picture":
        return format_picture_type(json_data, show_full_answers)
    elif structure_type == "collector.read":
        return format_read_type(json_data)
    elif structure_type == "collector.repeat_essay":
        return format_repeat_essay(json_data)
    elif structure_type == "collector.repeat_dialogue":
        return format_repeat_dialogue(json_data)
    elif structure_type == "collector.word":
        return format_word_type(json_data)
    elif structure_type == "collector.choose":
        return format_choose_type(json_data, show_full_answers)
    return json.dumps(json_data, indent=4, ensure_ascii=False)

def format_role_type(json_data, show_full_answers):
    result = []
    info = json_data.get("info", {})
    questions = info.get("question", [])
    if "value" in info and info["value"]:
        cleaned_dialog = clean_html_tags(info["value"])
        result.append("==对话内容==")
        result.append(cleaned_dialog)
        result.append("")
    for idx, question in enumerate(questions, 1):
        raw_ask = question.get("ask", "")
        cleaned_ask = clean_html_tags(raw_ask)
        cleaned_ask = re.sub(r"ets_th\d+\s*", "", cleaned_ask)
        ask_text = cleaned_ask.strip()
        result.append(f"题目 {idx}：{ask_text}")
        if "keywords" in question and question["keywords"]:
            result.append(f"关键词：{question['keywords']}")
        std_options = question.get("std", [])
        if std_options:
            result.append("答案选项：")
            display_options = std_options if show_full_answers else std_options[:3]
            for i, opt in enumerate(display_options, 1):
                raw_value = opt.get('value', '')
                cleaned_value = clean_html_tags(raw_value)
                result.append(f"{i}. {cleaned_value.strip()}")
            if not show_full_answers and len(std_options) > 3:
                result.append(f"... 还有{len(std_options)-3}个答案未显示（可勾选显示完整答案）")
            result.append("")
    return "\n".join(result)

def format_picture_type(json_data, show_full_answers):
    result = []
    info = json_data.get("info", {})
    if "topic" in info and info["topic"]:
        result.append(f"==主题：{info['topic']}==")
        result.append("")
    if "image" in info and info["image"]:
        result.append(f"图片：{info['image']}")
        result.append("")
    if "value" in info and info["value"]:
        cleaned_text = clean_html_tags(info["value"])
        result.append("==内容描述==")
        result.append(cleaned_text.replace("</br>", "\n").strip())
        result.append("")
    if "keypoint" in info and info["keypoint"]:
        cleaned_keypoints = clean_html_tags(info["keypoint"])
        result.append("==核心要点==")
        points = re.split(r"(?=\d+\. )", cleaned_keypoints)
        for point in [p.strip() for p in points if p.strip()]:
            result.append(point)
        result.append("")
    std_options = info.get("std", [])
    if std_options:
        result.append("==参考答案==")
        display_options = std_options if show_full_answers else std_options[:3]
        for i, opt in enumerate(display_options, 1):
            cleaned_answer = clean_html_tags(opt.get("value", ""))
            cleaned_answer = re.sub(r"\n\s*\n", "\n", cleaned_answer).strip()
            result.append(f"答案 {i}：")
            result.append(cleaned_answer)
            result.append("")
        if not show_full_answers and len(std_options) > 3:
            result.append(f"... 还有{len(std_options)-3}个答案未显示（可勾选显示完整答案）")
            result.append("")
    return "\n".join(result)

def format_choose_type(json_data, show_full_answers=True):
    result = []
    info = json_data.get("info", {})
    result.append("==选择题==")
    result.append("")
    st_nr = clean_html_tags(info.get("st_nr", ""))
    if st_nr:
        result.append("题目描述：")
        result.append(st_nr)
        result.append("")
    xtlist = info.get("xtlist", [])
    is_single_question = len(xtlist) == 1
    answer_summary = []
    for idx, xt_item in enumerate(xtlist, 1):
        answer = xt_item.get("answer", "")
        if answer:
            if is_single_question:
                answer_summary.append(f"正确答案：{answer}")
            else:
                answer_summary.append(f"第 {idx} 题：{answer}")
    if answer_summary:
        if not is_single_question:
            result.append("正确答案汇总：")
        result.extend(answer_summary)
        result.append("")
    for idx, xt_item in enumerate(xtlist, 1):
        xt_nr = clean_html_tags(xt_item.get("xt_nr", ""))
        if xt_nr:
            if is_single_question:
                result.append(f"{xt_nr}")
            else:
                result.append(f"第 {idx} 题：{xt_nr}")
            result.append("")
        xxlist = xt_item.get("xxlist", [])
        if xxlist:
            result.append("选项：")
            for option in xxlist:
                xx_mc = option.get("xx_mc", "")
                xx_nr = clean_html_tags(option.get("xx_nr", ""))
                if xx_mc and xx_nr:
                    result.append(f"  {xx_mc}. {xx_nr}")
            result.append("")
    return "\n".join(result)

def format_read_type(json_data):
    result = []
    info = json_data.get("info", {})
    result.append("==阅读材料==")
    result.append("")
    if "value" in info and info["value"]:
        cleaned_text = clean_html_tags(info["value"])
        formatted_text = cleaned_text.replace("</br>", "\n").strip()
        result.append(formatted_text)
        result.append("")
    return "\n".join(result)

def format_repeat_essay(json_data):
    result = []
    info = json_data.get("info", {})
    result.append("==问答短文==")
    result.append("")
    if "value" in info and info["value"]:
        cleaned_text = clean_html_tags(info["value"])
        result.append(cleaned_text.replace("</br>", "\n").strip())
        result.append("")
    sublist = info.get("sublist", [])
    if sublist:
        result.append("==参考翻译==")
        for item in sublist:
            if "text" in item and "translate" in item:
                result.append(f"{clean_html_tags(item['text'])}")
                result.append(f"  → {clean_html_tags(item['translate'])}")
                result.append("")
    return "\n".join(result)

def format_repeat_dialogue(json_data):
    result = []
    info = json_data.get("info", {})
    result.append("==对话内容==")
    result.append("")
    if "value" in info and info["value"]:
        cleaned_text = clean_html_tags(info["value"])
        result.append(cleaned_text.replace("</br>", "\n").strip())
        result.append("")
    sublist = info.get("sublist", [])
    if sublist:
        result.append("==详细对话==")
        for item in sublist:
            if "role" in item and "text" in item:
                result.append(f"{item['role']}: {clean_html_tags(item['text'])}")
                if "translate" in item:
                    result.append(f"  → {clean_html_tags(item['translate'])}")
                result.append("")
    return "\n".join(result)

def format_word_type(json_data):
    result = []
    info = json_data.get("info", {})
    result.append("==词汇问答==")
    result.append("")
    value_content = clean_html_tags(info.get("value", ""))
    translate_content = clean_html_tags(info.get("translate", ""))
    if value_content and translate_content and not re.search(r"[?]", value_content):
        result.append("原文内容：")
        result.append(value_content)
        result.append("")
        result.append("参考翻译：")
        result.append(translate_content)
        result.append("")
    else:
        if value_content:
            result.append("原文内容：")
            items = re.split(r"(?=What|Who|How|Why|Where|When|Which)", value_content)
            for item in [i.strip() for i in items if i.strip()]:
                result.append(item)
            result.append("")
        if translate_content:
            result.append("参考翻译：")
            trans_items = re.split(r"(?=(What|Who|How|Why|Where|When|Which|A strong wind) )", translate_content)
            for i in range(0, len(trans_items), 2):
                if i+1 < len(trans_items):
                    question_part = trans_items[i+1].strip()
                    answer_part = trans_items[i].strip()
                    if question_part:
                        combined = f"{question_part}{answer_part}"
                        processed_text = re.sub(r"([。！？])", r"\1\n", combined)
                        result.append(processed_text.strip())
                        result.append("")
    return "\n".join(result)


class ContentJsonViewer(wx.Panel):
    def __init__(self, parent: wx.Window):
        super().__init__(parent)
        self.activate_exam_dir = ""
        self.contents = []
        self.content_names = []
        self.content_index = 0
        self.ctrl_down = False
        self.pretty_print_enabled = True
        self.show_full_answers = False
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pretty_print_checkbox = wx.CheckBox(self, label="启用美观输出")
        self.pretty_print_checkbox.SetValue(True)
        self.pretty_print_checkbox.Bind(wx.EVT_CHECKBOX, self.on_pretty_print_toggle)
        self.full_answers_checkbox = wx.CheckBox(self, label="显示完整答案")
        self.full_answers_checkbox.SetValue(False)
        self.full_answers_checkbox.Bind(wx.EVT_CHECKBOX, self.on_full_answers_toggle)
        self.export_btn = wx.Button(self, label="导出为TXT")
        self.export_btn.Bind(wx.EVT_BUTTON, self.export_to_txt)
        self.option_sizer.Add(self.pretty_print_checkbox, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        self.option_sizer.Add(self.full_answers_checkbox, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        self.option_sizer.Add(self.export_btn, proportion=0, flag=wx.LEFT | wx.RIGHT, border=10)
        self.sizer.Add(self.option_sizer, proportion=0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)

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

    def on_pretty_print_toggle(self, event: wx.CommandEvent):
        self.pretty_print_enabled = event.IsChecked()
        self.full_answers_checkbox.Enable(event.IsChecked())
        if self.contents:
            self.content_change()

    def on_full_answers_toggle(self, event: wx.CommandEvent):
        self.show_full_answers = event.IsChecked()
        if self.contents and self.pretty_print_enabled:
            self.content_change()

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
        return 0 <= self.content_index < len(self.contents)

    def content_change(self):
        self.content_dir_text.SetLabel(f"当前目录：{self.content_names[self.content_index]}")
        self.top_sizer.Layout()
        if self.pretty_print_enabled:
            formatted_content = format_question_json(
                self.contents[self.content_index],
                show_full_answers=self.show_full_answers
            )
        else:
            formatted_content = json.dumps(self.contents[self.content_index], indent=4, ensure_ascii=False)
        self.json_viewer.SetValue(formatted_content)

    def init_data(self, dir_path: str):
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
        self.content_change()

    def export_to_txt(self, event: wx.CommandEvent):
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

GetSystemMetrics = windll.user32.GetSystemMetrics
MAX_SIZE = (GetSystemMetrics(0), GetSystemMetrics(1))

class Viewer(wx.Frame):
    def __init__(self, parent: wx.Frame):
        super().__init__(parent, title="ETSViewer", size=(820, 780))
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
        if self.ts_parent_dir:
            self.load_dir(self.ts_parent_dir)

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
        if isdir(path_join(roaming_dir, "ETS")):
            self.load_dir(path_join(roaming_dir, "ETS"))
        else:
            wx.MessageBox("未找到ETS文件夹", "错误", wx.OK | wx.ICON_ERROR, parent=self)

    def load_choose_dir(self, *_):
        with wx.DirDialog(self, "选择文件夹") as dir_dlg:
            if dir_dlg.ShowModal() == wx.ID_OK:
                self.load_dir(dir_dlg.GetPath())

    def load_dir(self, dir_path: str):
        self.open_menu.Enable(2, True)
        self.ts_parent_dir = dir_path
        self.ts_list.load_dir(dir_path)

if __name__ == "__main__":
    app = wx.App()
    viewer = Viewer(None)
    viewer.Show()
    app.MainLoop()
