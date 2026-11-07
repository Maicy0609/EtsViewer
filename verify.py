"""
题库过滤验证脚本

逐词校验格式化输出是否「不漏、不多、不乱序、不泄漏标签」，
并覆盖本机没有真实数据的题型（用内置 fixture）。

用法：
    python verify.py                 # 自动定位 %APPDATA%\\ETS
    python verify.py --root D:\\题库   # 指定目录
    python verify.py --skip-ui       # 跳过 wx 控件链路（无 GUI 环境时用）
"""
import argparse
import collections
import html
import json
import os
import re
import sys
from collections.abc import Iterator
from os.path import expandvars, isdir, join
from typing import Any

from formatters import format_question_json
from utils import clean_html_tags  # noqa: F401  供 run_clean_contract 使用

TOKEN_RE = re.compile(r"[A-Za-z]+|[0-9]+|[\u4e00-\u9fff]")
DIGIT_RE = re.compile(r"^[0-9]+$")
ETS_DIR_RE = re.compile(r"[0-9A-F]{20,}")
_REF_TAG_RE = re.compile(r"<[^>]*>")

# 格式化函数自己拼的固定文案，不算「多出来的词」
_HEADER_TEXT = [
    "对话内容", "题目", "关键词", "答案选项", "主题", "图片", "题目要求",
    "内容描述", "核心要点", "参考答案", "答案", "参考范文", "阅读材料",
    "参考翻译", "解析", "选择题", "题目描述", "选项", "正确答案", "汇总",
    "第", "题", "还有", "个", "未显示", "可勾选", "显示完整答案",
    "原文内容", "词汇问答", "问答短文", "对话复述", "详细对话",
]
HEADER_TOKENS: set[str] = set()
for _s in _HEADER_TEXT:
    HEADER_TOKENS.update(TOKEN_RE.findall(_s))


def toks(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def ref_clean(text: str) -> str:
    """独立于 utils.clean_html_tags 的参考清理

    刻意不复用被测代码：否则 clean_html_tags 本身过度删除或漏删时，
    期望值和实际值会一起偏移，校验就失效了。
    标签一律替换成空格，避免把相邻单词粘成一个词（这正好能检出「粘连」类错误）。
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = _REF_TAG_RE.sub(" ", text)
    return html.unescape(text)


def contiguous(needle: list[str], hay: list[str]) -> bool:
    """needle 是否作为连续子序列出现在 hay 中"""
    n = len(needle)
    if n == 0:
        return True
    for i in range(len(hay) - n + 1):
        if hay[i:i + n] == needle:
            return True
    return False


def find_root() -> str | None:
    """复现 main.py 的自动识别逻辑"""
    roaming = expandvars(r"%APPDATA%")
    if isdir(roaming):
        for name in sorted(os.listdir(roaming)):
            if ETS_DIR_RE.match(name) and isdir(join(roaming, name)):
                return join(roaming, name)
        if isdir(join(roaming, "ETS")):
            return join(roaming, "ETS")
    return None


def iter_contents(root: str) -> Iterator[tuple[str, str, str]]:
    for exam in sorted(os.listdir(root)):
        ep = join(root, exam)
        if not isdir(ep):
            continue
        for sub in sorted(os.listdir(ep)):
            sp = join(ep, sub)
            f = join(sp, "content.json")
            if isdir(sp) and sub.startswith("content") and os.path.exists(f):
                yield exam, sub, f


def expected_fields(data: Any) -> list[str]:
    """按格式化函数的展示意图，收集「应该出现在输出里」的原始文本"""
    if not isinstance(data, dict):
        return []
    st = data.get("structure_type")
    raw_info = data.get("info")
    info: dict[str, Any] = raw_info if isinstance(raw_info, dict) else {}
    out: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value.strip():
            out.append(value)

    def add_options(options: object, key: str = "value") -> None:
        for opt in options if isinstance(options, list) else []:
            add((opt or {}).get(key) if isinstance(opt, dict) else opt)

    if st == "collector.role":
        add(info.get("value"))
        for q in info.get("question") or []:
            if not isinstance(q, dict):
                continue
            ask = ref_clean(q.get("ask", ""))
            add(re.sub(r"ets_th\d+\s*", "", ask))
            add(ref_clean(q.get("keywords", "")))
            add(q.get("answer"))
            add(q.get("analyze"))
            add_options(q.get("std"))
    elif st == "collector.read":
        for key in ("value", "translate", "analyze"):
            add(info.get(key))
    elif st == "collector.picture":
        for key in ("topic", "image", "value", "analyze", "keypoint", "ref"):
            add(info.get(key))
        add_options(info.get("std"))
    elif st == "collector.choose":
        add(info.get("st_nr"))
        for xt in info.get("xtlist") or []:
            if not isinstance(xt, dict):
                continue
            add(xt.get("xt_nr"))
            add(xt.get("answer"))
            for opt in xt.get("xxlist") or []:
                if isinstance(opt, dict):
                    add(opt.get("xx_nr"))
                    add(opt.get("xx_mc"))
    else:  # word / repeat_essay / repeat_dialogue
        add(info.get("value"))
        add(info.get("translate"))
        for item in info.get("sublist") or []:
            if isinstance(item, dict):
                add(item.get("role"))
                add(item.get("text"))
                add(item.get("translate"))
    return out


def check_one(data: Any) -> dict[str, Any]:
    """对单份 content.json 做逐词校验"""
    out = format_question_json(data, show_full_answers=True)
    expected: collections.Counter[str] = collections.Counter()
    for raw in expected_fields(data):
        expected.update(toks(ref_clean(raw)))
    actual = collections.Counter(toks(out))

    missing = expected - actual
    extra = collections.Counter({
        k: v for k, v in (actual - expected).items()
        if k not in HEADER_TOKENS and not DIGIT_RE.match(k)
    })

    # 顺序：每个字段的 token 应原样连续出现
    hay = toks(out)
    order_bad = 0
    for raw in expected_fields(data):
        seq = toks(ref_clean(raw))
        if len(seq) >= 6 and not contiguous(seq, hay):
            order_bad += 1

    # 标签泄漏：绕过 clean_html_tags 直接拼接的字段
    leaks = 0
    raw_info = data.get("info") if isinstance(data, dict) else None
    info: dict[str, Any] = raw_info if isinstance(raw_info, dict) else {}
    for q in info.get("question") or []:
        kw = (q or {}).get("keywords") if isinstance(q, dict) else None
        if isinstance(kw, str) and re.search(r"<[^>]+>", kw):
            leaks += 1
    for key in ("topic", "image"):
        val = info.get(key)
        if isinstance(val, str) and re.search(r"<[^>]+>", val):
            leaks += 1

    return {
        "missing": sum(missing.values()),
        "extra": sum(extra.values()),
        "order_bad": order_bad,
        "leaks": leaks,
        "missing_sample": missing.most_common(3),
        "extra_sample": extra.most_common(3),
    }


FIXTURES: list[tuple[str, dict[str, Any]]] = [
    ("choose-多题", {
        "structure_type": "collector.choose",
        "info": {"st_nr": "<p>阅读下面的材料，选择正确答案。</p>", "xtlist": [
            {"xt_nr": "1. 文章的主旨是什么？", "answer": "B", "xxlist": [
                {"xx_mc": "A", "xx_nr": "介绍一种植物</br>"},
                {"xx_mc": "B", "xx_nr": "说明环境保护的重要性</br>"}]},
            {"xt_nr": "2. 作者的态度是？", "answer": "A", "xxlist": [
                {"xx_mc": "A", "xx_nr": "支持"}]}]}}),
    ("choose-单题", {
        "structure_type": "collector.choose",
        "info": {"st_nr": "选出与录音内容相符的一项。", "xtlist": [
            {"xt_nr": "", "answer": "C", "xxlist": [
                {"xx_mc": "C", "xx_nr": "They will meet at the library.</br>"}]}]}}),
    ("word-问句", {
        "structure_type": "collector.word",
        "info": {"value": "What is the weather like? It is sunny.",
                 "translate": "天气怎么样？晴天。"}}),
    ("word-陈述", {
        "structure_type": "collector.word",
        "info": {"value": "A strong wind is coming.", "translate": "大风要来了。"}}),
    ("repeat_essay", {
        "structure_type": "collector.repeat_essay",
        "info": {"value": "<p>请听短文并复述主要内容。</p>",
                 "sublist": [{"text": "The story is about a brave girl.",
                              "translate": "这个故事讲的是一个勇敢的女孩。"}]}}),
    ("repeat_dialogue", {
        "structure_type": "collector.repeat_dialogue",
        "info": {"value": "<p>请听对话并复述。</p>", "sublist": [
            {"role": "W", "text": "Where are you going?", "translate": "你要去哪？"},
            {"role": "M", "text": "To the library.", "translate": "去图书馆。"}]}}),
    ("未知题型", {
        "structure_type": "collector.unknown",
        "info": {"value": "<p>未识别的题型应回退为原始 JSON。</p>"}}),
]


def run_fixtures() -> list[tuple[str, str]]:
    """跑内置 fixture，返回失败项"""
    failures: list[tuple[str, str]] = []
    for name, data in FIXTURES:
        if data.get("structure_type") == "collector.unknown":
            out = format_question_json(data, show_full_answers=True)
            if "collector.unknown" not in out:
                failures.append((name, "回退输出异常"))
            continue
        res = check_one(data)
        if res["missing"] or res["extra"] or res["order_bad"] or res["leaks"]:
            failures.append((name, json.dumps(res, ensure_ascii=False)))
    return failures


def run_clean_contract() -> list[str]:
    """clean_html_tags 的格式契约：换行标签必须变成换行，不能整段吞掉"""
    cases = [
        ("<p>a</p><p>b</p>", "a\nb"),
        ("<p>第一段</p><p>第二段</p>", "第一段\n第二段"),
        ("a</br>b", "a\nb"),
        ("a<br>b", "a\nb"),
        ("a<br/>b", "a\nb"),
        ("<i>a</i>", "a"),
        ("a &amp; b", "a & b"),
        ("<span class=\"italic\">x</span>", "x"),
        ("", ""),
    ]
    failures: list[str] = []
    for raw, want in cases:
        got = clean_html_tags(raw)
        if got != want:
            failures.append(f"{raw!r} -> {got!r}（期望 {want!r}）")
    if clean_html_tags(None) != "":
        failures.append("None 未返回空串")
    return failures


def run_ui(root: str) -> list[str]:
    """真实目录走一遍控件链路：加载 + 逐条渲染"""
    import wx  # 延迟导入，--skip-ui 时不需要
    from widgets import ContentJsonViewer

    app = wx.App(False)  # type: ignore[no-untyped-call]  # noqa: F841
    frame = wx.Frame(None)
    problems: list[str] = []
    for exam in sorted(os.listdir(root)):
        ep = join(root, exam)
        if not isdir(ep):
            continue
        viewer = ContentJsonViewer(frame)
        try:
            viewer.init_data(ep)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{exam}: init_data 抛 {type(exc).__name__}")
            continue
        expected_dirs = [s for s in os.listdir(ep)
                         if s.startswith("content") and isdir(join(ep, s))
                         and os.path.exists(join(ep, s, "content.json"))]
        if len(viewer.contents) != len(expected_dirs):
            problems.append(f"{exam}: 条目数 {len(viewer.contents)} != {len(expected_dirs)}")
        for i in range(len(viewer.contents)):
            viewer.content_index = i
            viewer._content_change()  # noqa: SLF001
            if not viewer.json_viewer.GetValue().strip():
                problems.append(f"{exam}/{viewer.content_names[i]}: 渲染为空")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="题库过滤验证")
    parser.add_argument("--root", help="题库根目录，默认自动识别 %%APPDATA%%\\ETS")
    parser.add_argument("--skip-ui", action="store_true", help="跳过 wx 控件链路")
    args = parser.parse_args()

    root = args.root or find_root()
    print("=" * 60)
    if root and isdir(root):
        print(f"题库目录: {root}")
        stats: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
        bad_files: list[str] = []
        for exam, sub, path in iter_contents(root):
            with open(path, encoding="utf-8") as fp:
                data = json.load(fp)
            st = data.get("structure_type") if isinstance(data, dict) else "?"
            res = check_one(data)
            stats[str(st)][0] += 1
            if res["missing"] or res["extra"] or res["order_bad"] or res["leaks"]:
                stats[str(st)][1] += 1
                bad_files.append(f"{exam}/{sub}: {res['missing_sample']} "
                                 f"{res['extra_sample']} order={res['order_bad']} "
                                 f"leak={res['leaks']}")
        total = sum(v[0] for v in stats.values())
        bad = sum(v[1] for v in stats.values())
        print(f"\n[真实数据] 共 {total} 份 content.json")
        for st, (n, b) in sorted(stats.items()):
            flag = "OK" if b == 0 else f"{b} 份异常"
            print(f"  {st:<24} {n:>3} 份   {flag}")
        for line in bad_files[:10]:
            print("    !", line)
        if not args.skip_ui:
            ui_problems = run_ui(root)
            print(f"\n[控件链路] 异常 {len(ui_problems)} 项")
            for line in ui_problems[:10]:
                print("    !", line)
            bad += len(ui_problems)
    else:
        print("未找到题库目录，跳过真实数据校验（可用 --root 指定）")
        bad = 0

    print(f"\n[内置 fixture] 覆盖 choose / word / repeat_essay / repeat_dialogue")
    fixture_failures = run_fixtures()
    print(f"  共 {len(FIXTURES)} 组，失败 {len(fixture_failures)}")
    for name, detail in fixture_failures:
        print(f"    ! {name}: {detail}")
    bad += len(fixture_failures)

    print("\n[清理契约] 换行/实体/空值")
    contract_failures = run_clean_contract()
    print(f"  共 10 项，失败 {len(contract_failures)}")
    for detail in contract_failures:
        print(f"    ! {detail}")
    bad += len(contract_failures)

    print("\n" + "=" * 60)
    print("结果: 全部通过" if bad == 0 else f"结果: {bad} 项异常")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
