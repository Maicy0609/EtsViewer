"""
JSON格式化模块
包含各种题型内容的格式化输出函数
"""
import re
import json
from typing import Any, Callable

from utils import clean_html_tags

# 题型的参考答案默认展示条数
DEFAULT_ANSWER_LIMIT = 3

# 词汇问答里用来切分句子的英文疑问词
_QUESTION_SPLIT_RE = re.compile(
    r"(?=(?:What|Who|How|Why|Where|When|Which|A strong wind)\b)"
)

Formatter = Callable[[], str]


def _as_dict(value: object) -> dict[str, Any]:
    """安全地把任意值当作 dict 使用"""
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    """安全地把任意值当作 list 使用"""
    return value if isinstance(value, list) else []


def _limited(options: list[Any], show_full_answers: bool) -> list[Any]:
    """按开关截断参考答案列表"""
    if show_full_answers:
        return options
    return options[:DEFAULT_ANSWER_LIMIT]


def _hidden_hint(total: int) -> str:
    """未显示答案时的提示文案"""
    return f"... 还有{total - DEFAULT_ANSWER_LIMIT}个答案未显示（可勾选显示完整答案）"


def format_question_json(json_data: Any, show_full_answers: bool = True) -> str:
    """根据题型选择对应的格式化函数"""
    if not isinstance(json_data, dict):
        # content.json 可能是数组/字符串等非对象结构，直接原样输出，避免 AttributeError
        return json.dumps(json_data, indent=4, ensure_ascii=False)

    data: dict[str, Any] = json_data
    structure_type = data.get("structure_type")
    formatters: dict[Any, Formatter] = {
        "collector.role": lambda: format_role_type(data, show_full_answers),
        "collector.picture": lambda: format_picture_type(data, show_full_answers),
        "collector.read": lambda: format_read_type(data),
        "collector.repeat_essay": lambda: format_repeat_essay(data),
        "collector.repeat_dialogue": lambda: format_repeat_dialogue(data),
        "collector.word": lambda: format_word_type(data),
        "collector.choose": lambda: format_choose_type(data, show_full_answers),
    }
    formatter = formatters.get(structure_type)
    if formatter is not None:
        return formatter()
    return json.dumps(data, indent=4, ensure_ascii=False)


def format_role_type(json_data: dict[str, Any], show_full_answers: bool = True) -> str:
    """格式化角色扮演题型"""
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    questions = _as_list(info.get("question"))

    if info.get("value"):
        cleaned_dialog = clean_html_tags(info["value"])
        result.append("==对话内容==")
        result.append(cleaned_dialog)
        result.append("")

    for idx, question in enumerate(questions, 1):
        question = _as_dict(question)
        raw_ask = question.get("ask", "")
        cleaned_ask = clean_html_tags(raw_ask)
        cleaned_ask = re.sub(r"ets_th\d+\s*", "", cleaned_ask)
        ask_text = cleaned_ask.strip()
        result.append(f"题目 {idx}：{ask_text}")

        if question.get("keywords"):
            result.append(f"关键词：{question['keywords']}")

        # answer / analyze 在本机题库里全为空，但字段确实存在，非空时不能丢
        if question.get("answer"):
            result.append(f"参考答案：{clean_html_tags(question['answer'])}")

        if question.get("analyze"):
            result.append(f"解析：{clean_html_tags(question['analyze'])}")

        std_options = _as_list(question.get("std"))
        if std_options:
            result.append("答案选项：")
            for i, opt in enumerate(_limited(std_options, show_full_answers), 1):
                cleaned_value = clean_html_tags(_as_dict(opt).get("value", ""))
                result.append(f"{i}. {cleaned_value.strip()}")
            if not show_full_answers and len(std_options) > DEFAULT_ANSWER_LIMIT:
                result.append(_hidden_hint(len(std_options)))
            result.append("")

    return "\n".join(result)


def format_picture_type(json_data: dict[str, Any], show_full_answers: bool = True) -> str:
    """格式化图片描述题型"""
    result: list[str] = []
    info = _as_dict(json_data.get("info"))

    if info.get("topic"):
        result.append(f"==主题：{info['topic']}==")
        result.append("")

    if info.get("image"):
        result.append(f"图片：{info['image']}")
        result.append("")

    # analyze 里是题目指令/材料提示，真实题库中 11/11 非空，不能丢
    if info.get("analyze"):
        result.append("==题目要求==")
        result.append(clean_html_tags(info["analyze"]))
        result.append("")

    if info.get("value"):
        cleaned_text = clean_html_tags(info["value"])
        result.append("==内容描述==")
        result.append(cleaned_text)
        result.append("")

    if info.get("keypoint"):
        cleaned_keypoints = clean_html_tags(info["keypoint"])
        result.append("==核心要点==")
        points = re.split(r"(?=\d+\. )", cleaned_keypoints)
        for point in [p.strip() for p in points if p.strip()]:
            result.append(point)
        result.append("")

    std_options = _as_list(info.get("std"))
    if std_options:
        result.append("==参考答案==")
        for i, opt in enumerate(_limited(std_options, show_full_answers), 1):
            cleaned_answer = clean_html_tags(_as_dict(opt).get("value", ""))
            result.append(f"答案 {i}：")
            result.append(cleaned_answer)
            result.append("")
        if not show_full_answers and len(std_options) > DEFAULT_ANSWER_LIMIT:
            result.append(_hidden_hint(len(std_options)))
            result.append("")

    if info.get("ref"):
        result.append("==参考范文==")
        result.append(clean_html_tags(info["ref"]))
        result.append("")

    return "\n".join(result)


def format_choose_type(json_data: dict[str, Any], show_full_answers: bool = True) -> str:
    """格式化选择题题型

    ``show_full_answers`` 为 False 时隐藏答案汇总，只保留题干与选项。
    """
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    result.append("==选择题==")
    result.append("")

    st_nr = clean_html_tags(info.get("st_nr", ""))
    if st_nr:
        result.append("题目描述：")
        result.append(st_nr)
        result.append("")

    xtlist = _as_list(info.get("xtlist"))
    is_single_question = len(xtlist) == 1

    # 答案汇总
    answer_summary: list[str] = []
    if show_full_answers:
        for idx, xt_item in enumerate(xtlist, 1):
            answer = _as_dict(xt_item).get("answer", "")
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
        xt_item = _as_dict(xt_item)
        xt_nr = clean_html_tags(xt_item.get("xt_nr", ""))
        if xt_nr:
            if is_single_question:
                result.append(f"{xt_nr}")
            else:
                result.append(f"第 {idx} 题：{xt_nr}")
            result.append("")

        xxlist = _as_list(xt_item.get("xxlist"))
        if xxlist:
            result.append("选项：")
            for option in xxlist:
                option = _as_dict(option)
                xx_mc = option.get("xx_mc", "")
                xx_nr = clean_html_tags(option.get("xx_nr", ""))
                if xx_mc and xx_nr:
                    result.append(f"  {xx_mc}. {xx_nr}")
            result.append("")

    return "\n".join(result)


def format_read_type(json_data: dict[str, Any]) -> str:
    """格式化阅读理解题型

    只取 ``value``：``ai`` / ``symbol`` 是同一篇文章的副本，且源数据里
    ``</br>`` 被删掉时没补空格（"weather</br>is" → "weatheris"），显示出来反而更差。
    """
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    result.append("==阅读材料==")
    result.append("")

    if info.get("value"):
        result.append(clean_html_tags(info["value"]))
        result.append("")

    if info.get("translate"):
        result.append("==参考翻译==")
        result.append(clean_html_tags(info["translate"]))
        result.append("")

    if info.get("analyze"):
        result.append("==解析==")
        result.append(clean_html_tags(info["analyze"]))
        result.append("")

    return "\n".join(result)


def format_repeat_essay(json_data: dict[str, Any]) -> str:
    """格式化问答短文题型"""
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    result.append("==问答短文==")
    result.append("")

    if info.get("value"):
        result.append(clean_html_tags(info["value"]))
        result.append("")

    sublist = _as_list(info.get("sublist"))
    if sublist:
        result.append("==参考翻译==")
        for item in sublist:
            item = _as_dict(item)
            if "text" in item and "translate" in item:
                result.append(clean_html_tags(item["text"]))
                result.append(f"  → {clean_html_tags(item['translate'])}")
                result.append("")

    return "\n".join(result)


def format_repeat_dialogue(json_data: dict[str, Any]) -> str:
    """格式化对话复述题型"""
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    result.append("==对话内容==")
    result.append("")

    if info.get("value"):
        result.append(clean_html_tags(info["value"]))
        result.append("")

    sublist = _as_list(info.get("sublist"))
    if sublist:
        result.append("==详细对话==")
        for item in sublist:
            item = _as_dict(item)
            if "role" in item and "text" in item:
                result.append(f"{item['role']}: {clean_html_tags(item['text'])}")
                if "translate" in item:
                    result.append(f"  → {clean_html_tags(item['translate'])}")
                result.append("")

    return "\n".join(result)


def format_word_type(json_data: dict[str, Any]) -> str:
    """格式化词汇问答题型

    原文按英文疑问词切句；译文若无法切成相同段数，则整段输出，
    避免出现「参考翻译」标题下面一片空白。
    """
    result: list[str] = []
    info = _as_dict(json_data.get("info"))
    result.append("==词汇问答==")
    result.append("")

    value_content = clean_html_tags(info.get("value", ""))
    translate_content = clean_html_tags(info.get("translate", ""))

    if not value_content and not translate_content:
        return "\n".join(result)

    # 陈述句：原文 + 整段翻译
    if not value_content or "?" not in value_content:
        if value_content:
            result.append("原文内容：")
            result.append(value_content)
            result.append("")
        if translate_content:
            result.append("参考翻译：")
            result.append(translate_content)
            result.append("")
        return "\n".join(result)

    # 问句：按疑问词切分
    questions = [s.strip() for s in _QUESTION_SPLIT_RE.split(value_content) if s.strip()]
    translations = [s.strip() for s in _QUESTION_SPLIT_RE.split(translate_content) if s.strip()]

    if questions and len(translations) == len(questions):
        result.append("原文内容：")
        for question, translation in zip(questions, translations):
            result.append(question)
            result.append(f"  → {translation}")
            result.append("")
        return "\n".join(result)

    result.append("原文内容：")
    result.extend(questions)
    result.append("")
    if translate_content:
        result.append("参考翻译：")
        result.append(translate_content)
        result.append("")

    return "\n".join(result)
