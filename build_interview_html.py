#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从面试题 Markdown 生成可视化 HTML（纯标准库构建）"""

import html
import re
import json
import shutil
import argparse
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent
ASSETS_DIR = DESKTOP / "assets"
SOURCE_DIR = DESKTOP / "sources" / "测试开发面试题解答"

MD_FILE = DESKTOP / "测开面试_通用版_含答案.md"
DEFAULT_EXTRA_MD_FILES = [DESKTOP / "测开面经.md"]
OUT_FILE_INDEX = DESKTOP / "index.html"
CHAPTERS_DIR = DESKTOP / "chapters"
SEARCH_INDEX_FILE = ASSETS_DIR / "search-index.json"
MERGE_REPORT_FILE = DESKTOP / "去重合并报告.md"
SUMMARY_FILE = SOURCE_DIR / "测试开发与AI_Agent面试题汇总.md"

TECH_CATEGORY_ORDER = [
    "测试流程与设计",
    "接口测试",
    "接口自动化框架",
    "pytest",
    "接口依赖与业务链路",
    "数据库与数据校验",
    "Linux / 日志分析",
    "性能测试",
    "CI/CD 与测试左移",
    "精准测试",
    "自动化测试平台",
    "LLM 基础与 Prompt",
    "RAG 知识增强",
    "AI Agent 自动执行",
    "AI 工具生态与能力扩展",
    "AI 测试与评测",
    "LLMOps 工程化工具",
    "UI 自动化",
    "兼容性 / 弱网",
    "安全权限",
    "代码实战",
    "综合追问 / 高频必问",
]

SOURCE_CATEGORY_BY_FILE = {
    "01-接口自动化框架设计.md": "接口自动化框架",
    "02-pytest深入.md": "pytest",
    "03-接口依赖与业务链路.md": "接口依赖与业务链路",
    "04-数据库与数据校验.md": "数据库与数据校验",
    "05-性能测试.md": "性能测试",
    "06-CICD与测试左移.md": "CI/CD 与测试左移",
    "07-精准测试.md": "精准测试",
    "08-自动化测试平台.md": "自动化测试平台",
    "09-AI_Agent基础.md": "AI Agent / RAG / AI 测试",
    "10-AI与测试开发结合.md": "AI Agent / RAG / AI 测试",
    "11-代码实战.md": "代码实战",
    "12-综合追问.md": "综合追问 / 高频必问",
    "13-30分钟高频必问.md": "综合追问 / 高频必问",
    "14-补充题.md": "综合追问 / 高频必问",
    "15-AI工程化工具.md": "LLMOps 工程化工具",
    "16-AI工具生态与能力扩展.md": "AI 工具生态与能力扩展",
}

# 章节 -> 稳定的 ASCII slug，用于生成 chapters/<slug>.html 的文件名与跨页链接
CATEGORY_SLUG = {
    "测试流程与设计": "process-design",
    "接口测试": "api-test",
    "接口自动化框架": "api-automation",
    "pytest": "pytest",
    "接口依赖与业务链路": "api-dependency",
    "数据库与数据校验": "database",
    "Linux / 日志分析": "linux-log",
    "性能测试": "performance",
    "CI/CD 与测试左移": "cicd",
    "精准测试": "precise-test",
    "自动化测试平台": "platform",
    "LLM 基础与 Prompt": "llm-prompt",
    "RAG 知识增强": "rag",
    "AI Agent 自动执行": "ai-agent",
    "AI 工具生态与能力扩展": "ai-tools",
    "AI 测试与评测": "ai-evaluation",
    "LLMOps 工程化工具": "llmops",
    "UI 自动化": "ui-automation",
    "兼容性 / 弱网": "compatibility",
    "安全权限": "security",
    "代码实战": "coding",
    "综合追问 / 高频必问": "comprehensive",
}


def category_slug(title: str, index: int) -> str:
    return CATEGORY_SLUG.get(title) or f"chapter-{index}"


def escape(s: str) -> str:
    return html.escape(s, quote=True)


def attr_escape(s: str) -> str:
    """用于 HTML 属性：转义并去掉换行，避免破坏标签结构"""
    return escape(s).replace("\n", " ").replace("\r", " ").replace("\t", " ")


def inline_md(text: str) -> str:
    """粗体、行内代码"""
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


# 圈号序号 ①-⑳，用于拆分为分行列表
CN_CIRCLE_NUMS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
CN_SPLIT_RE = re.compile("(?=[" + CN_CIRCLE_NUMS + "])")
BOLD_QUESTION_RE = re.compile(r"^\*\*(?P<title>[^*\n]*?/[^*\n]*?)\*\*(?P<rest>.*)$")
TABLE_SEPARATOR_RE = re.compile(r":?-{3,}:?")


def render_paragraph_text(text: str) -> str:
    """段落：含圈号序号时拆成逐条列表，否则普通段落"""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return ""

    if not any(c in text for c in CN_CIRCLE_NUMS):
        return f"<p>{inline_md(text)}</p>"

    parts = [p.strip().rstrip("；;") for p in CN_SPLIT_RE.split(text) if p.strip()]
    if len(parts) < 2:
        return f"<p>{inline_md(text)}</p>"

    intro_parts: list[str] = []
    list_items: list[str] = []
    for p in parts:
        if p and p[0] in CN_CIRCLE_NUMS:
            list_items.append(p)
        else:
            intro_parts.append(p)

    html_chunks: list[str] = []
    if intro_parts:
        html_chunks.append(f"<p>{inline_md(' '.join(intro_parts))}</p>")
    if list_items:
        lis = "".join(f"<li>{inline_md(item)}</li>" for item in list_items)
        html_chunks.append(f'<ul class="point-list">{lis}</ul>')

    return "".join(html_chunks) if html_chunks else f"<p>{inline_md(text)}</p>"


def is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]


def split_table_row(line: str) -> list[str]:
    """拆分 Markdown 表格行，保留转义管道符为单元格内容。"""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]

    cells: list[str] = []
    buf: list[str] = []
    escaped = False
    for ch in row:
        if escaped:
            if ch == "|":
                buf.append("|")
            else:
                buf.append("\\")
                buf.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if escaped:
        buf.append("\\")
    cells.append("".join(buf).strip())
    return cells


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(TABLE_SEPARATOR_RE.fullmatch(cell.strip()) for cell in cells)


def render_table(lines: list[str]) -> str:
    rows = [split_table_row(line) for line in lines]
    header = rows[0]
    body_rows = rows[2:]
    col_count = len(header)

    def padded(row: list[str]) -> list[str]:
        return (row + [""] * col_count)[:col_count]

    head_html = "".join(f"<th>{inline_md(cell)}</th>" for cell in padded(header))
    body_html = "".join(
        "<tr>" + "".join(f"<td>{inline_md(cell)}</td>" for cell in padded(row)) + "</tr>"
        for row in body_rows
    )
    return (
        '<div class="table-wrap"><table class="markdown-table">'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{body_html}</tbody>"
        "</table></div>"
    )


def block_md(lines: list[str]) -> str:
    """将答案块行列表转为 HTML"""
    out: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph(buf: list[str]):
        if buf:
            text = " ".join(s.strip() for s in buf if s.strip())
            if text:
                out.append(render_paragraph_text(text))
            buf.clear()

    para_buf: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.rstrip("\n")

        # 代码块
        if stripped.startswith("```"):
            flush_paragraph(para_buf)
            lang = stripped[3:].strip() or "text"
            i += 1
            code_lines = []
            while i < n and not lines[i].rstrip("\n").startswith("```"):
                code_lines.append(lines[i].rstrip("\n"))
                i += 1
            if i < n:
                i += 1
            code = escape("\n".join(code_lines))
            out.append(f'<pre class="code-block" data-lang="{escape(lang)}"><code>{code}</code></pre>')
            continue

        # 表格
        if i + 1 < n and is_table_row(stripped) and is_table_separator(lines[i + 1].rstrip("\n")):
            flush_paragraph(para_buf)
            table_lines = [stripped, lines[i + 1].rstrip("\n")]
            i += 2
            while i < n and is_table_row(lines[i].rstrip("\n")):
                table_lines.append(lines[i].rstrip("\n"))
                i += 1
            out.append(render_table(table_lines))
            continue

        # 无序列表
        if re.match(r"^[-*]\s+", stripped):
            flush_paragraph(para_buf)
            items = []
            while i < n:
                ln = lines[i].rstrip("\n")
                if re.match(r"^[-*]\s+", ln):
                    item = re.sub(r"^[-*]\s+", "", ln)
                    sub = []
                    j = i + 1
                    while j < n:
                        sub_ln = lines[j].rstrip("\n")
                        if re.match(r"^\s+[-*]\s+", sub_ln):
                            sub.append(re.sub(r"^\s+[-*]\s+", "", sub_ln))
                            j += 1
                        else:
                            break
                    sub_html = "<ul>" + "".join(f"<li>{inline_md(s)}</li>" for s in sub) + "</ul>" if sub else ""
                    items.append(f"<li>{inline_md(item)}{sub_html}</li>")
                    i = j
                else:
                    break
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph(para_buf)
            items = []
            while i < n:
                ln = lines[i].rstrip("\n")
                if re.match(r"^\d+\.\s+", ln):
                    item = re.sub(r"^\d+\.\s+", "", ln)
                    sub = []
                    j = i + 1
                    while j < n:
                        sub_ln = lines[j].rstrip("\n")
                        if re.match(r"^\s+[-*]\s+", sub_ln):
                            sub.append(re.sub(r"^\s+[-*]\s+", "", sub_ln))
                            j += 1
                        elif not sub_ln.strip():
                            j += 1
                        else:
                            break
                    sub_html = "<ul>" + "".join(f"<li>{inline_md(s)}</li>" for s in sub) + "</ul>" if sub else ""
                    items.append(f"<li>{inline_md(item)}{sub_html}</li>")
                    i = j
                else:
                    break
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # 空行
        if not stripped.strip() or stripped.strip() == "---":
            flush_paragraph(para_buf)
            i += 1
            continue

        # 答案内小标题
        if stripped.startswith("### "):
            flush_paragraph(para_buf)
            out.append(f'<h4 class="answer-subtitle">{inline_md(stripped[4:].strip())}</h4>')
            i += 1
            continue
        if stripped.startswith("#### "):
            flush_paragraph(para_buf)
            out.append(f'<h5 class="answer-subtitle small">{inline_md(stripped[5:].strip())}</h5>')
            i += 1
            continue

        # **问题**： / **答**：
        m_prob = re.match(r"^\*\*问题\*\*[：:]\s*(.*)$", stripped)
        m_ans = re.match(r"^\*\*答\*\*[：:]\s*(.*)$", stripped)
        if m_prob:
            flush_paragraph(para_buf)
            rest = m_prob.group(1).strip()
            if rest:
                out.append(f'<div class="problem-inline"><span class="badge badge-problem">问题</span> {inline_md(rest)}</div>')
            i += 1
            continue
        if m_ans:
            flush_paragraph(para_buf)
            rest = m_ans.group(1).strip()
            if rest:
                para_buf.append(rest)
            i += 1
            continue

        para_buf.append(stripped)
        i += 1

    flush_paragraph(para_buf)
    return "\n".join(out)


def parse_md(content: str) -> dict:
    content = content.lstrip("\ufeff")
    lines = content.splitlines(keepends=True)
    intro_lines: list[str] = []
    parts: list[dict] = []
    current_part: dict | None = None
    current_q: dict | None = None
    answer_buf: list[str] = []
    global_idx = 0

    def structural_scan() -> dict[str, int | str | bool]:
        h1_count = h2_count = h2_q_titles = answer_markers = bold_questions = 0
        first_h1_seen = False
        first_h1_before_h2_has_next_h1 = False
        in_code = False

        for raw in lines:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue

            if line.startswith("# ") and not line.startswith("## "):
                h1_count += 1
                if first_h1_seen and h2_count == 0:
                    first_h1_before_h2_has_next_h1 = True
                first_h1_seen = True
            elif line.startswith("## "):
                h2_count += 1
                if re.match(r"^##\s+Q\d+\b", line, re.IGNORECASE):
                    h2_q_titles += 1

            if re.match(r"^\*\*答\*\*[：:]", line):
                answer_markers += 1
            if BOLD_QUESTION_RE.match(line):
                bold_questions += 1

        parser_mode = "bold_question" if bold_questions and not answer_markers and not h2_q_titles else "heading_question"
        return {
            "mode": parser_mode,
            "first_h1_is_intro": parser_mode == "bold_question" or first_h1_before_h2_has_next_h1,
        }

    scan = structural_scan()
    mode = str(scan["mode"])
    first_h1_is_intro = bool(scan["first_h1_is_intro"])
    skipped_intro_h1 = False

    def start_part(title: str):
        nonlocal current_part
        finish_part()
        current_part = {
            "id": f"part-{len(parts)}",
            "title": title,
            "questions": [],
        }

    def ensure_part():
        if current_part is None:
            start_part("未分组")

    def start_question(title: str, rest: str = ""):
        nonlocal current_q, answer_buf
        ensure_part()
        finish_question()
        is_scenario = title.startswith("场景")
        current_q = {
            "type": "scenario" if is_scenario else "question",
            "title": title,
            "problem_text": "",
            "answer_html": "",
            "search_text": title,
        }
        answer_buf = []
        rest = rest.strip()
        if rest.startswith(("：", ":")):
            rest = rest[1:].strip()
        if rest:
            append_answer_line(rest)

    def append_part_line(raw: str):
        # 章节标题后、首个问题前的散文目前无展示位（章节会按技术分类重组），
        # 仅保留文档开头、首个章节之前的内容作为 intro。
        if current_part is None and raw.strip() and raw.strip() != "---":
            intro_lines.append(raw)

    def append_answer_line(raw: str):
        answer_buf.append(raw)

    def finish_question():
        nonlocal current_q, answer_buf, global_idx
        if current_q is not None:
            global_idx += 1
            body = block_md(answer_buf) if answer_buf else ""
            current_q["global_idx"] = global_idx
            current_q["answer_html"] = body
            current_q["search_text"] = (
                current_q.get("title", "")
                + " "
                + current_q.get("problem_text", "")
                + " "
                + "\n".join(answer_buf)
            )
            if current_part is not None:
                current_part["questions"].append(current_q)
        current_q = None
        answer_buf = []

    def finish_part():
        nonlocal current_part
        finish_question()
        if current_part is not None:
            parts.append(current_part)
        current_part = None

    i = 0
    in_code_block = False
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        stripped = line.strip()
        is_fence = stripped.startswith("```")

        if not in_code_block and line.startswith("# ") and not line.startswith("## "):
            if mode == "heading_question" and not skipped_intro_h1 and first_h1_is_intro:
                skipped_intro_h1 = True
            elif mode == "heading_question":
                start_part(line[2:].strip())
            else:
                if line[2:].strip():
                    intro_lines.append(line[2:].strip())
            i += 1
            continue

        if not in_code_block and line.startswith("## "):
            title = line[3:].strip()
            if mode == "bold_question":
                start_part(title)
            else:
                start_question(title)
            i += 1
            continue

        if not in_code_block and mode == "bold_question":
            m_bold_q = BOLD_QUESTION_RE.match(line)
            if m_bold_q:
                start_question(m_bold_q.group("title").strip(), m_bold_q.group("rest"))
                i += 1
                continue

        if not in_code_block and current_q is not None and stripped == "---":
            finish_question()
            i += 1
            continue

        if current_q is None:
            append_part_line(raw)
            if is_fence:
                in_code_block = not in_code_block
            i += 1
            continue

        m_prob_only = None if in_code_block else re.match(r"^\*\*问题\*\*[：:]\s*(.*)$", line)
        if m_prob_only is not None:
            current_q["problem_text"] = m_prob_only.group(1).strip()
            i += 1
            continue

        if not in_code_block and re.match(r"^\*\*答\*\*[：:]", line):
            rest = re.sub(r"^\*\*答\*\*[：:]\s*", "", line)
            if rest.strip():
                append_answer_line(rest)
            i += 1
            continue

        append_answer_line(raw)
        if is_fence:
            in_code_block = not in_code_block
        i += 1

    finish_part()

    intro_html = ""
    if intro_lines:
        buf = [l.rstrip("\n") for l in intro_lines if l.strip() and l.strip() != "---"]
        items = []
        for l in buf:
            if l.startswith(">"):
                items.append(l.lstrip("> ").strip())
            elif not l.startswith("#"):
                items.append(l.strip())
        if items:
            intro_html = "".join(f"<p>{inline_md(x)}</p>" for x in items)

    return {"intro_html": intro_html, "parts": parts, "total_questions": global_idx}


def extract_q_id(title: str) -> str:
    m = re.match(r"^\s*Q(?P<num>\d+)\b", title, re.IGNORECASE)
    return f"Q{m.group('num')}" if m else ""


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "")


def normalize_title(title: str) -> str:
    text = title.lower().strip()
    text = re.sub(r"^q\d+\s*[：:、.\-\s]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+\s*[.、：:\-\s]*", "", text)
    text = re.sub(r"[“”\"'`（）()\[\]【】<>《》？?！!，,。；;：:\s/_\-]+", "", text)
    for prefix in [
        "请介绍一下", "请介绍", "你的", "你们", "你在项目中", "你项目里",
        "如何", "怎么", "怎样", "什么是", "为什么", "是否", "有没有",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    replacements = {
        "是如何设计的": "设计",
        "如何设计": "设计",
        "怎么设计": "设计",
        "如何使用": "使用",
        "怎么使用": "使用",
        "有什么区别": "区别",
        "有哪些": "",
        "是什么": "",
        "的作用是什么": "作用",
        "作用是什么": "作用",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def clean_title_for_display(title: str) -> str:
    text = (title or "").strip()
    text = re.sub(r"^\s*Q?\d+(?:[.&．]\d+)*\s*[：:、.\-/]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*\d+(?:\s*[&/]\s*\d+)*\s*/\s*", "", text)
    text = re.sub(r"^\s*\d+(?:\s*[&/]\s*\d+)*\s*[.、：:\-]\s*", "", text)
    text = re.sub(r"^\s*第\s*\d+\s*[题问]\s*[：:、.\-]?\s*", "", text)
    return text.strip() or (title or "").strip()


def answer_depth_score(question: dict) -> int:
    html_text = question.get("answer_html", "")
    plain = strip_tags(html_text)
    score = min(len(plain) // 80, 12)
    score += html_text.count("<pre") * 5
    score += html_text.count("<table") * 3
    for keyword in ["边界", "异常", "排查", "定位", "为什么", "风险", "落地", "实现", "代码", "重试", "超时", "幂等", "线程", "连接池"]:
        if keyword in plain:
            score += 2
    source = question.get("source_file", "")
    if source in SOURCE_CATEGORY_BY_FILE:
        score += 8
    return score


def contains_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def infer_ai_category(part_title: str, question_title: str, source_file: str) -> str:
    """AI 方向按知识层拆分，避免 RAG / Agent / AI 测试继续混在同一章。"""
    part = part_title.lower()
    question = question_title.lower()
    text = f"{part} {question}"
    ai_source_files = {
        "09-AI_Agent基础.md",
        "10-AI与测试开发结合.md",
        "15-AI工程化工具.md",
        "16-AI工具生态与能力扩展.md",
    }
    ai_context_keywords = [
        "ai", "agent", "rag", "mcp", "skill", "skills", "llm", "prompt",
        "大模型", "知识库", "embedding", "function calling",
        "function tools", "llmops", "toolops", "工程化工具", "能力扩展",
        "智能通知", "业务文档智能生成",
    ]
    if source_file not in ai_source_files and not contains_any(text, ai_context_keywords):
        return ""

    tool_keywords = [
        "mcp", "function calling", "function tools", "tool calling",
        "skills", "skill", "plugins", "plugin", "toolops", "fastmcp",
        "tools、resources、prompts", "resources、prompts", "playwright mcp",
        "工具生态", "能力扩展", "工具接入", "工具注册", "工具路由",
        "工具发现", "工具返回格式", "工具调用失败", "工具误调用", "mcp tool",
    ]
    if contains_any(question, tool_keywords):
        return "AI 工具生态与能力扩展"

    ai_eval_keywords = [
        "ai 测试", "大模型应用测试", "llm-as-judge", "golden set",
        "评测", "评估", "准确率", "召回率", "忠实度", "幻觉率",
        "幻觉检测", "越狱", "prompt injection", "生成测试用例",
        "用例质量", "测试集", "回归测试", "安全测试", "测试用例",
        "怎么测试", "如何测试", "测试难点", "怎么验证", "如何验证",
        "怎么发现", "如何发现", "如何判断", "怎么判断", "怎么评估",
        "如何评估", "如何构造", "测试报告", "回归", "合规",
        "准确", "敏感内容", "不确定", "错误", "失败", "不稳定",
        "唯一答案", "人工评审", "审核", "质量", "用例", "阈值", "达标",
        "校验", "归档", "怎么处理", "如何处理", "不严谨", "review",
        "提交代码", "生产环境操作", "人工编辑", "人工确认", "风险", "拦截",
    ]
    if contains_any(question, ai_eval_keywords) or (
        contains_any(part, ["大模型应用测试", "ai 测试"]) and contains_any(question, ["测试", "质量", "评估", "准确", "合规"])
    ):
        return "AI 测试与评测"

    rag_keywords = [
        "rag", "embedding", "向量", "向量数据库", "chunk", "topk", "top-k",
        "rerank", "混合检索", "知识库", "检索", "召回", "引用来源",
        "文档切分", "文档解析", "多跳", "faithfulness",
        "文档清洗", "清洗和切分", "过期文档",
    ]
    if contains_any(question, rag_keywords) or contains_any(part, ["rag 知识库"]):
        return "RAG 知识增强"

    agent_keywords = [
        "agent", "react", "planning", "memory", "workflow", "multi-agent",
        "任务拆解", "自主决策", "工具选择", "无限循环", "记忆管理",
        "自动化测试 agent", "帮我测试", "环境感知", "tools 模块",
        "短期记忆", "长期记忆", "reflection", "feedback", "安全控制模块",
    ]
    if contains_any(question, agent_keywords):
        return "AI Agent 自动执行"

    llmops_keywords = [
        "llmops", "工程化工具", "模型路由", "模型 fallback", "fallback",
        "a/b", "灰度", "可观测", "链路追踪", "trace", "token",
        "成本", "缓存", "部署", "服务化", "限流", "网关", "治理",
        "审计", "监控", "日志", "版本管理",
    ]
    if contains_any(question, llmops_keywords):
        return "LLMOps 工程化工具"

    llm_keywords = [
        "llm", "大模型", "prompt", "提示词", "temperature", "上下文窗口",
        "多模态", "chatgpt",
    ]
    if contains_any(question, llm_keywords) or contains_any(part, ["ai / agent / skills", "ai 应用"]):
        return "LLM 基础与 Prompt"

    if source_file in {"09-AI_Agent基础.md", "10-AI与测试开发结合.md"}:
        return "AI Agent 自动执行"
    return ""


def infer_category(part_title: str, question_title: str, source_file: str) -> str:
    ai_category = infer_ai_category(part_title, question_title, source_file)
    if ai_category:
        return ai_category

    if source_file in SOURCE_CATEGORY_BY_FILE:
        return SOURCE_CATEGORY_BY_FILE[source_file]

    text = f"{part_title} {question_title}".lower()
    rules = [
        ("接口自动化框架", ["接口自动化框架", "requests", "yaml", "allure", "断言模块", "日志模块", "request_util"]),
        ("pytest", ["pytest", "fixture", "conftest", "marker", "参数化", "pytest.ini", "xdist", "rerun"]),
        ("接口依赖与业务链路", ["接口依赖", "业务链路", "token 过期", "登录", "下单", "支付", "数据依赖"]),
        ("数据库与数据校验", ["sql", "数据库", "数据校验", "落库", "事务", "索引", "对账", "数据迁移"]),
        ("Linux / 日志分析", ["linux", "日志", "traceid", "端口", "进程", "磁盘", "cpu", "内存"]),
        ("性能测试", ["性能", "jmeter", "压测", "tps", "qps", "并发", "响应时间", "瓶颈"]),
        ("CI/CD 与测试左移", ["jenkins", "ci/cd", "cicd", "流水线", "质量门禁", "测试左移"]),
        ("精准测试", ["精准测试", "变更", "用例映射", "覆盖率"]),
        ("自动化测试平台", ["测试平台", "平台设计", "高可用", "任务调度"]),
        ("LLM 基础与 Prompt", ["ai", "大模型", "prompt", "llm", "模型"]),
        ("UI 自动化", ["ui 自动化", "playwright", "selenium", "page object", "locator"]),
        ("兼容性 / 弱网", ["兼容", "弱网", "charles", "移动端", "android", "ios"]),
        ("安全权限", ["安全", "权限", "越权", "rbac", "token 篡改", "prompt injection"]),
        ("代码实战", ["手写", "代码实战", "写一个", "封装代码", "动态参数"]),
        ("综合追问 / 高频必问", ["综合", "追问", "高频", "速记", "补充题", "区别"]),
        ("接口测试", ["接口", "http", "get", "post", "cookie", "session", "jwt", "状态码"]),
        ("测试流程与设计", ["测试流程", "需求", "测试计划", "测试报告", "缺陷", "用例"]),
    ]
    for category, keywords in rules:
        if any(k.lower() in text for k in keywords):
            return category
    return "综合追问 / 高频必问"


def annotate_document(doc: dict, source_path: Path) -> dict:
    for part in doc.get("parts", []):
        part["source_file"] = source_path.name
        original_title = part.get("title", "")
        for question in part.get("questions", []):
            question["source_file"] = source_path.name
            question["source_part"] = original_title
            question["q_id"] = extract_q_id(question.get("title", ""))
    return doc


def parse_summary_followups(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    followups: dict[str, list[str]] = {}
    current_q = ""
    collecting = False
    buf: list[str] = []

    def flush():
        nonlocal buf
        if current_q and buf:
            followups[current_q] = [line + "\n" for line in buf]
        buf = []

    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("## Q"):
            flush()
            current_q = extract_q_id(line[3:].strip())
            collecting = False
            continue
        if not in_code and line.startswith("### "):
            if line[4:].strip().startswith("追问"):
                collecting = True
                buf = ["**追问**："]
                continue
            if collecting:
                collecting = False
        if collecting and current_q:
            buf.append(line)
    flush()
    return {key: block_md(value) for key, value in followups.items()}


def append_followups(documents: list[dict], followups: dict[str, str]) -> None:
    if not followups:
        return
    for doc in documents:
        for part in doc.get("parts", []):
            for question in part.get("questions", []):
                q_id = question.get("q_id")
                if q_id and q_id in followups and followups[q_id] not in question.get("answer_html", ""):
                    question["answer_html"] += f'\n<div class="followup-block">{followups[q_id]}</div>'
                    question["search_text"] += " " + strip_tags(followups[q_id])


def parse_summary_followup_cards(path: Path) -> list[dict]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    groups: list[dict] = []
    current_q = ""
    current_title = ""
    collecting = False
    items: list[str] = []
    current_item = ""
    in_code = False

    def finish_item():
        nonlocal current_item
        item = current_item.strip()
        if item:
            items.append(item)
        current_item = ""

    def flush_group():
        nonlocal items
        finish_item()
        if current_q and items:
            groups.append({
                "q_id": current_q,
                "parent_title": current_title,
                "items": items,
            })
        items = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
        if in_code:
            continue

        if line.startswith("## Q"):
            flush_group()
            current_title = line[3:].strip()
            current_q = extract_q_id(current_title)
            collecting = False
            continue

        if line.startswith("### "):
            if line[4:].strip().startswith("追问"):
                collecting = True
                continue
            if collecting:
                collecting = False
                finish_item()
            continue

        if not collecting:
            continue

        if not stripped or stripped == "---":
            finish_item()
            continue

        numbered = re.match(r"^\s*\d+[.)、]\s*(.+)$", line)
        bulleted = re.match(r"^\s*[-*]\s+(.+)$", line)
        if numbered or bulleted:
            finish_item()
            current_item = (numbered or bulleted).group(1).strip()
        elif current_item:
            current_item += " " + stripped

    flush_group()
    return groups


def build_parent_question_index(documents: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for doc in documents:
        for part in doc.get("parts", []):
            for question in part.get("questions", []):
                q_id = question.get("q_id")
                if not q_id:
                    continue
                if q_id not in index or answer_depth_score(question) > answer_depth_score(index[q_id]):
                    index[q_id] = question
    return index


def answer_blocks(answer_html: str) -> list[str]:
    return re.findall(
        r"<(?:p|li|h4|h5|pre|ul|ol|div)\b[^>]*>.*?</(?:p|li|h4|h5|pre|ul|ol|div)>",
        answer_html or "",
        flags=re.DOTALL,
    )


def answer_segments(answer_html: str) -> list[str]:
    blocks = answer_blocks(answer_html)
    if not blocks:
        return []

    segments: list[list[str]] = []
    current: list[str] = []

    def starts_section(block: str) -> bool:
        plain = strip_tags(block).strip()
        if not plain:
            return False
        return bool(re.match(r"^(?:\d+(?:[./&]\d+)*|[a-zA-Z])\s*[.、：:)]", plain))

    for block in blocks:
        if starts_section(block) and current:
            segments.append(current)
            current = [block]
        else:
            current.append(block)

    if current:
        segments.append(current)

    return ["\n".join(segment) for segment in segments if strip_tags("\n".join(segment)).strip()]


def score_answer_block(question_text: str, block_html: str) -> int:
    plain_question = strip_tags(question_text).lower()
    plain_block = strip_tags(block_html).lower()
    ascii_tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_./-]*", plain_question)
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", plain_question)
    chinese_tokens: set[str] = set()
    for chunk in chinese_chunks:
        if len(chunk) <= 6:
            chinese_tokens.add(chunk)
        else:
            chinese_tokens.update(chunk[i:i + 2] for i in range(len(chunk) - 1))
            chinese_tokens.update(chunk[i:i + 3] for i in range(len(chunk) - 2))

    score = 0
    for token in ascii_tokens:
        if token and token in plain_block:
            score += 4
    for token in chinese_tokens:
        if token and token in plain_block:
            score += 2
    for chunk in chinese_chunks:
        if len(chunk) >= 3 and chunk in plain_block:
            score += min(len(chunk), 8)
    return score


def clean_standalone_answer_html(answer_html: str) -> str:
    html_out = answer_html
    html_out = re.sub(
        r"(<(?:p|li|h4|h5)\b[^>]*>\s*(?:<strong>)?)\d+(?:[./&]\d+)*\s*[.、：:)]\s*",
        r"\1",
        html_out,
    )
    html_out = re.sub(
        r"(<(?:p|li|h4|h5)\b[^>]*>\s*(?:<strong>)?)\d+\s*/\s*\d+\s*[.、：:)]\s*",
        r"\1",
        html_out,
    )
    return html_out


def standalone_answer_override(question_text: str) -> str:
    normalized = normalize_title(question_text)
    plain = re.sub(r"[\s`*_./-]+", "", question_text.lower())
    if "pytest" in plain and "插件" in plain and "conftest" in plain:
        return block_md([
            "pytest 插件是可复用、可分发的扩展包，适合沉淀跨项目通用能力；conftest.py 是当前项目或当前目录树内的本地 fixture / hook 配置文件，适合放项目级共享前后置。",
            "- 作用范围：插件通常通过安装或配置后全项目可用；conftest.py 按目录层级生效，当前目录及子目录自动可用。",
            "- 复用方式：插件适合多个仓库复用；conftest.py 更适合本项目内部组织 fixture。",
            "- 维护边界：通用能力放插件，业务强相关的登录、造数、清理、环境切换放 conftest.py。",
        ])
    return ""


def derive_followup_answer(parent: dict | None, question_text: str, followup_index: int | None = None) -> str:
    override = standalone_answer_override(question_text)
    if override:
        return override

    if not parent:
        return block_md([
            f"这题要直接围绕“{question_text}”回答，先给结论，再说明项目中的落地方式和边界。",
            "- 结论：用一句话回答当前问题，不要绕回原始大题。",
            "- 落地：说明代码、配置、目录、流程或平台里具体放在哪里、怎么执行。",
            "- 边界：补充适用条件、风险点和排查方式。",
        ])

    blocks = answer_segments(parent.get("answer_html", ""))
    if followup_index:
        numbered = []
        for idx, block in enumerate(blocks):
            plain = strip_tags(block).strip()
            if re.match(rf"^{followup_index}(?:[./&]\d+)*\s*[.、：:)]", plain):
                numbered.append((idx, block))
            elif re.match(rf"^\d+(?:[./&]\d+)*\s*/\s*{followup_index}\b", plain):
                numbered.append((idx, block))
        if numbered:
            return clean_standalone_answer_html(numbered[0][1])

    scored: list[tuple[int, int, str]] = [
        (score_answer_block(question_text, block), idx, block)
        for idx, block in enumerate(blocks)
    ]
    scored = sorted(scored, key=lambda item: (-item[0], item[1]))
    top_score = scored[0][0] if scored else 0
    min_score = max(4, top_score)
    selected_idx = [
        idx for score, idx, _ in scored
        if score >= min_score and score > 0
    ][:1]

    if not selected_idx and blocks:
        selected_idx = [scored[0][1]] if scored else [0]

    selected = [blocks[idx] for idx in sorted(selected_idx)]
    if not selected:
        selected = [f"<p>{inline_md(strip_tags(parent.get('answer_html', ''))[:260])}</p>"]

    return clean_standalone_answer_html("\n".join(selected))


def build_followup_card_document(documents: list[dict], followup_groups: list[dict], source_path: Path) -> dict:
    parent_index = build_parent_question_index(documents)
    parts_by_category: dict[str, dict] = {}

    for group in followup_groups:
        parent = parent_index.get(group.get("q_id", ""))
        parent_title = group.get("parent_title", "")
        category = infer_category(
            parent.get("source_part", "") if parent else parent_title,
            parent.get("title", parent_title) if parent else parent_title,
            parent.get("source_file", source_path.name) if parent else source_path.name,
        )
        part = parts_by_category.setdefault(category, {
            "id": f"followup-{len(parts_by_category)}",
            "title": category,
            "questions": [],
        })

        for idx, item in enumerate(group.get("items", []), 1):
            title = f"{group.get('q_id', 'Q')}.{idx}：{item}"
            answer_html = derive_followup_answer(parent, item, idx)
            part["questions"].append({
                "type": "question",
                "title": title,
                "problem_text": "",
                "answer_html": answer_html,
                "search_text": f"{title} {strip_tags(answer_html)}",
                "source_file": source_path.name,
                "source_part": parent_title,
                "q_id": f"{group.get('q_id', 'Q')}.{idx}",
            })

    return {
        "intro_html": "",
        "parts": list(parts_by_category.values()),
        "total_questions": sum(len(part["questions"]) for part in parts_by_category.values()),
    }


def regroup_and_dedup(documents: list[dict]) -> tuple[dict, list[dict]]:
    buckets = {category: [] for category in TECH_CATEGORY_ORDER}
    duplicates: list[dict] = []
    seen: dict[tuple[str, str], dict] = {}

    for doc in documents:
        for part in doc.get("parts", []):
            part_title = part.get("title", "")
            for question in part.get("questions", []):
                category = infer_category(part_title, question.get("title", ""), question.get("source_file", ""))
                key = (category, normalize_title(question.get("title", "")))
                if len(key[1]) < 4:
                    key = (category, normalize_title(question.get("title", "") + question.get("source_part", "")))
                candidate = dict(question)
                candidate["category"] = category

                if key not in seen:
                    seen[key] = candidate
                    buckets.setdefault(category, []).append(candidate)
                    continue

                existing = seen[key]
                existing_score = answer_depth_score(existing)
                candidate_score = answer_depth_score(candidate)
                if candidate_score > existing_score:
                    existing.update(candidate)
                    action = "替换为更深答案"
                else:
                    action = "保留原答案，跳过重复"
                same_source_same_title = (
                    existing.get("source_file") == candidate.get("source_file")
                    and existing.get("title") == candidate.get("title")
                )
                if not same_source_same_title:
                    duplicates.append({
                        "category": category,
                        "key": key[1],
                        "kept": existing.get("title", ""),
                        "duplicate": candidate.get("title", ""),
                        "kept_source": existing.get("source_file", ""),
                        "duplicate_source": candidate.get("source_file", ""),
                        "action": action,
                    })

    parts: list[dict] = []
    total = 0
    for idx, category in enumerate(TECH_CATEGORY_ORDER):
        questions = buckets.get(category, [])
        if not questions:
            continue
        part = {
            "id": f"part-{len(parts)}",
            "title": category,
            "slug": category_slug(category, len(parts) + 1),
            "questions": [],
        }
        for local_idx, question in enumerate(questions, start=1):
            total += 1
            original_title = question.get("original_title") or question.get("title", "")
            display_idx = f"Q{local_idx:03d}"
            clean_display_title = clean_title_for_display(original_title)
            question["original_title"] = original_title
            question["local_idx"] = local_idx
            question["display_idx"] = display_idx
            question["display_title"] = clean_display_title
            question["search_title"] = f"{display_idx}：{clean_display_title}"
            question["global_idx"] = total
            question["search_text"] = (
                f"{question['search_title']} {original_title} "
                + question.get("search_text", "")
            )
            part["questions"].append(question)
        parts.append(part)
    return {"intro_html": "", "parts": parts, "total_questions": total}, duplicates


def render_nav(parts: list[dict], prefix: str, current_slug: str | None) -> str:
    """侧边栏导航：跨页链接到各章节页，高亮当前页。

    prefix 为相对路径前缀：首页为 "chapters/"，章节页为 ""（同级）。
    """
    home_href = f"{prefix}index.html" if prefix else "../index.html"
    home_active = " active" if current_slug is None else ""
    items = [f'<li><a class="nav-home{home_active}" href="{home_href}">🏠 首页目录</a></li>']
    for part in parts:
        href = f"{prefix}{part['slug']}.html"
        active = " active" if part["slug"] == current_slug else ""
        count = len(part.get("questions", []))
        items.append(
            f'<li><a class="nav-chapter{active}" href="{href}">'
            f'{escape(part["title"])}<span class="nav-count">{count}</span></a></li>'
        )
    return "\n".join(items)


def render_card(item: dict) -> str:
    scenario_cls = " scenario" if item.get("type") == "scenario" else ""
    source = item.get("source_file", "")
    display_idx = item.get("display_idx") or f'#{item["global_idx"]}'
    display_title = item.get("display_title") or item.get("title", "")
    original_title = item.get("original_title", item.get("title", ""))
    source_meta = f'<span>来源：{escape(source)}</span>' if source else ""
    card_meta = ""
    if source_meta:
        card_meta = f'<div class="card-meta">{source_meta}</div>'
    problem = ""
    if item.get("problem_text"):
        problem = (
            '<div class="problem-block">'
            '<span class="badge badge-problem">场景问题</span>'
            f'<p>{inline_md(item["problem_text"])}</p>'
            '</div>'
        )
    return f"""
            <article class="card{scenario_cls}"
                     id="card-{item["global_idx"]}"
                     data-idx="{item["global_idx"]}"
                     data-search="{attr_escape(item.get("search_text", ""))}">
              <header class="card-header" role="button" tabindex="0" aria-expanded="false">
                <span class="card-index">{escape(display_idx)}</span>
                <div class="card-main">
                  <h3 class="card-title" title="原题：{attr_escape(original_title)}">{escape(display_title)}</h3>
                  {card_meta}
                </div>
                <div class="card-actions">
                  <button type="button" class="action-btn master-btn" title="标记为已掌握">✓</button>
                  <button type="button" class="action-btn star-btn" title="收藏">★</button>
                  <button type="button" class="toggle-btn">展开</button>
                </div>
              </header>
              <div class="card-body" hidden>
                {problem}
                <div class="answer-block">
                  <span class="badge badge-answer">参考答案</span>
                  <div class="answer-content">
                    {item.get("answer_html", "")}
                  </div>
                </div>
              </div>
            </article>
"""


def render_chapter_section(part: dict) -> str:
    cards = "\n".join(render_card(item) for item in part.get("questions", []))
    return f"""
        <section class="part-section" id="{part["id"]}">
          <h2 class="part-title">{escape(part["title"])}</h2>
          <p class="part-meta">{len(part.get("questions", []))} 题</p>
          <div class="cards-grid">
            {cards}
          </div>
        </section>
"""


def render_directory(parts: list[dict]) -> str:
    """首页章节目录卡片。"""
    cards = []
    for idx, part in enumerate(parts, start=1):
        count = len(part.get("questions", []))
        cards.append(f"""
            <a class="chapter-card" href="chapters/{part['slug']}.html">
              <span class="chapter-card-num">第 {idx} 章</span>
              <h3 class="chapter-card-title">{escape(part["title"])}</h3>
              <span class="chapter-card-meta">{count} 题</span>
            </a>""")
    return f'<div class="chapter-grid">{"".join(cards)}</div>'


def build_search_index(parts: list[dict]) -> list[dict]:
    """全局搜索索引：每题 idx / title / category / url / text。"""
    index = []
    for part in parts:
        url = f"chapters/{part['slug']}.html"
        for item in part.get("questions", []):
            text = strip_tags(item.get("answer_html", ""))
            text = re.sub(r"\s+", " ", text).strip()
            index.append({
                "idx": item["global_idx"],
                "display_idx": item.get("display_idx", f'#{item["global_idx"]}'),
                "title": item.get("search_title", item.get("display_title", item.get("title", ""))),
                "original_title": item.get("original_title", item.get("title", "")),
                "category": part["title"],
                "url": url,
                "text": f'{item.get("original_title", item.get("title", ""))} {text}',
            })
    return index


def render_topbar() -> str:
    return """
      <header class="topbar">
        <button type="button" class="menu-btn" id="menuBtn" aria-label="菜单">☰</button>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input type="search" id="search" placeholder="全局搜索题目、答案或关键词..." autocomplete="off">
          <div class="search-results" id="searchResults" hidden></div>
        </div>
        <div class="search-nav">
          <button type="button" id="searchPrev" disabled title="上一个 (↑)">↑</button>
          <button type="button" id="searchNext" disabled title="下一个 (↓)">↓</button>
        </div>
        <span class="search-stats" id="searchStats"></span>
        <div class="toolbar">
          <button type="button" id="randomBtn">随机一题</button>
          <button type="button" id="expandAll">全部展开</button>
          <button type="button" id="collapseAll">全部折叠</button>
          <button type="button" id="themeBtn">深色模式</button>
        </div>
      </header>
"""


def render_page(
    *,
    page_title: str,
    sidebar_title: str,
    css_content: str,
    js_content: str,
    parts: list[dict],
    total_questions: int,
    nav_prefix: str,
    current_slug: str | None,
    asset_prefix: str,
    body_html: str,
    search_index: list[dict],
) -> str:
    index_json = json.dumps(search_index, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(page_title)}</title>
  <style>
{css_content}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>
</head>
<body>
  <div class="app">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <h1>{escape(sidebar_title)}</h1>
        <div class="sub">含答案 · 共 {total_questions} 题</div>
      </div>
      <ul class="nav-list">
        {render_nav(parts, nav_prefix, current_slug)}
      </ul>
    </aside>

    <div class="main-wrap">
{render_topbar()}
      <main class="content">
{body_html}
      </main>
    </div>
  </div>

  <button type="button" class="back-top" id="backTop" aria-label="回到顶部">↑</button>

  <script>
    window.__BASE_PREFIX__ = "{asset_prefix}";
    window.__SEARCH_INDEX__ = {index_json};
  </script>
  <script>
{js_content}
  </script>
</body>
</html>
"""


def render_index_page(data: dict, page_title: str, sidebar_title: str, css_content: str, js_content: str, search_index: list[dict]) -> str:
    intro = f'<div class="intro">{data["intro_html"]}</div>' if data.get("intro_html") else ""
    body = f"""
        {intro}
        <section class="home-hero">
          <h2 class="home-title">{escape(sidebar_title)}</h2>
          <p class="home-sub">{len(data["parts"])} 章 / {data["total_questions"]} 题 · 按技术主题归档</p>
        </section>
        {render_directory(data["parts"])}
"""
    return render_page(
        page_title=page_title,
        sidebar_title=sidebar_title,
        css_content=css_content,
        js_content=js_content,
        parts=data["parts"],
        total_questions=data["total_questions"],
        nav_prefix="chapters/",
        current_slug=None,
        asset_prefix="",
        body_html=body,
        search_index=search_index,
    )


def render_chapter_page(part: dict, data: dict, page_title: str, sidebar_title: str, css_content: str, js_content: str, search_index: list[dict]) -> str:
    body = render_chapter_section(part)
    title = f"{part['title']} · {page_title}"
    return render_page(
        page_title=title,
        sidebar_title=sidebar_title,
        css_content=css_content,
        js_content=js_content,
        parts=data["parts"],
        total_questions=data["total_questions"],
        nav_prefix="",
        current_slug=part["slug"],
        asset_prefix="../",
        body_html=body,
        search_index=search_index,
    )


def write_merge_report(path: Path, duplicates: list[dict], data: dict, input_files: list[Path]) -> None:
    lines = [
        "# 去重合并报告",
        "",
        f"- 源文件数：{len(input_files)}",
        f"- 最终章节数：{len(data['parts'])}",
        f"- 最终题目数：{data['total_questions']}",
        f"- 识别并处理重复项：{len(duplicates)}",
        "",
        "## 源文件",
        "",
    ]
    lines.extend(f"- `{path.name}`" for path in input_files)
    lines.extend(["", "## 重复处理明细", ""])
    if not duplicates:
        lines.append("未发现明显重复项。")
    else:
        lines.append("| 分类 | 归一化键 | 保留题目 | 重复题目 | 动作 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in duplicates:
            lines.append(
                "| {category} | `{key}` | {kept}（{kept_source}） | {duplicate}（{duplicate_source}） | {action} |".format(
                    **{k: str(v).replace("|", "\\|") for k, v in item.items()}
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_input_file(value: str) -> Path:
    input_file = Path(value)
    if not input_file.exists():
        input_file = DESKTOP / value

    if not input_file.exists():
        raise SystemExit(f"找不到源文件: {input_file}")

    return input_file


def default_source_files() -> list[Path]:
    files = [MD_FILE] + [p for p in DEFAULT_EXTRA_MD_FILES if p.exists()]
    if SOURCE_DIR.exists():
        files.extend(
            path
            for path in sorted(SOURCE_DIR.glob("*.md"))
            if path.name not in {"README.md", SUMMARY_FILE.name}
        )
    return files


def normalize_html(html_out: str) -> str:
    return "\n".join(line.rstrip() for line in html_out.splitlines()) + "\n"


def main():
    parser = argparse.ArgumentParser(description="从面试题 Markdown 生成按章节拆分的多页可视化站点")
    parser.add_argument("--input", "-i", default=None, help="输入 Markdown 文件；不传时默认合并主库、补充面经和 sources 深度资料")
    parser.add_argument("--extra-input", action="append", default=[], help="追加合并的 Markdown 文件，可重复传入")
    parser.add_argument("--index-output", default=str(OUT_FILE_INDEX), help="首页/目录入口 HTML")
    parser.add_argument("--chapters-dir", default=str(CHAPTERS_DIR), help="各章节页面输出目录")
    parser.add_argument("--report-output", default=str(MERGE_REPORT_FILE), help="去重合并报告；传空字符串可关闭")
    parser.add_argument("--title", default="测开面试题库（通用版）", help="HTML 标题")
    parser.add_argument("--sidebar-title", default="测开面试题库", help="侧边栏标题")
    args = parser.parse_args()

    if args.input:
        input_files = [resolve_input_file(args.input)]
    else:
        input_files = default_source_files()
    input_files.extend(resolve_input_file(value) for value in args.extra_input)

    documents = [
        annotate_document(parse_md(path.read_text(encoding="utf-8-sig")), path)
        for path in input_files
    ]
    followup_groups = parse_summary_followup_cards(SUMMARY_FILE)
    if followup_groups:
        documents.append(build_followup_card_document(documents, followup_groups, SUMMARY_FILE))
    data, duplicates = regroup_and_dedup(documents)

    # Load Assets
    css_content = (ASSETS_DIR / "style.css").read_text(encoding="utf-8")
    js_content = (ASSETS_DIR / "script.js").read_text(encoding="utf-8")

    search_index = build_search_index(data["parts"])

    # 首页目录
    index_html = render_index_page(
        data, args.title, args.sidebar_title, css_content, js_content, search_index
    )
    Path(args.index_output).write_text(normalize_html(index_html), encoding="utf-8")

    # 每个章节一个页面（重建 chapters 目录，避免遗留旧 slug 文件）
    chapters_dir = Path(args.chapters_dir)
    if chapters_dir.exists():
        shutil.rmtree(chapters_dir)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for part in data["parts"]:
        page_html = render_chapter_page(
            part, data, args.title, args.sidebar_title, css_content, js_content, search_index
        )
        (chapters_dir / f"{part['slug']}.html").write_text(
            normalize_html(page_html), encoding="utf-8"
        )

    # 搜索索引（同时作为构建产物输出，便于外部复用）
    SEARCH_INDEX_FILE.write_text(
        json.dumps(search_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.report_output:
        report_inputs = input_files + ([SUMMARY_FILE] if followup_groups else [])
        write_merge_report(Path(args.report_output), duplicates, data, report_inputs)

    print(f"已生成首页: {args.index_output}")
    print(f"章节页目录: {chapters_dir}")
    print("源文件: " + " + ".join(path.name for path in input_files))
    print(f"章节数: {len(data['parts'])}, 题目数: {data['total_questions']}")
    print(f"独立扩展题: {sum(len(group.get('items', [])) for group in followup_groups)} 项")
    print(f"重复处理: {len(duplicates)} 项")


if __name__ == "__main__":
    main()
