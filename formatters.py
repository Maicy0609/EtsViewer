"""
JSON格式化模块
包含各种题型内容的格式化输出函数
"""
import re
import json
from utils import clean_html_tags


def format_question_json(json_data, show_full_answers=True):
    """根据题型选择对应的格式化函数"""
    structure_type = json_data.get("structure_type")
    formatters = {
        "collector.role": lambda: format_role_type(json_data, show_full_answers),
        "collector.picture": lambda: format_picture_type(json_data, show_full_answers),
        "collector.read": lambda: format_read_type(json_data),
        "collector.repeat_essay": lambda: format_repeat_essay(json_data),
        "collector.repeat_dialogue": lambda: format_repeat_dialogue(json_data),
        "collector.word": lambda: format_word_type(json_data),
        "collector.choose": lambda: format_choose_type(json_data, show_full_answers),
    }
    formatter = formatters.get(structure_type)
    if formatter:
        return formatter()
    return json.dumps(json_data, indent=4, ensure_ascii=False)


def format_role_type(json_data, show_full_answers):
    """格式化角色扮演题型"""
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
    """格式化图片描述题型"""
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
    """格式化选择题题型"""
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
    
    # 答案汇总
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
    
    # 题目详情
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
    """格式化阅读理解题型"""
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
    """格式化问答短文题型"""
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
    """格式化对话复述题型"""
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
    """格式化词汇问答题型"""
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
                if i + 1 < len(trans_items):
                    question_part = trans_items[i + 1].strip()
                    answer_part = trans_items[i].strip()
                    if question_part:
                        combined = f"{question_part}{answer_part}"
                        processed_text = re.sub(r"([。！？])", r"\1\n", combined)
                        result.append(processed_text.strip())
                        result.append("")
    
    return "\n".join(result)
