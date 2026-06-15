#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从面试题 Markdown 生成可视化 HTML（使用 Jinja2 模板）"""

import html
import re
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

DESKTOP = Path(__file__).resolve().parent
TEMPLATES_DIR = DESKTOP / "templates"
ASSETS_DIR = DESKTOP / "assets"

MD_FILE = DESKTOP / "测开面试_通用版_含答案.md"
DEFAULT_EXTRA_MD_FILES = [DESKTOP / "测开面经.md"]
OUT_FILE_ASCII = DESKTOP / "interview-qa-general.html"
OUT_FILE_INDEX = DESKTOP / "index.html"


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
        h1_count = h2_count = answer_markers = bold_questions = 0
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

            if re.match(r"^\*\*答\*\*[：:]", line):
                answer_markers += 1
            if BOLD_QUESTION_RE.match(line):
                bold_questions += 1

        parser_mode = "bold_question" if bold_questions and not answer_markers else "heading_question"
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
        if current_part is None:
            if raw.strip() and raw.strip() != "---":
                intro_lines.append(raw)
            return
        current_part.setdefault("freeform", []).append(raw)

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

    for p in parts:
        if p.get("freeform"):
            p["freeform_html"] = block_md([l.rstrip("\n") + "\n" for l in p["freeform"]])
            del p["freeform"]

    return {"intro_html": intro_html, "parts": parts, "total_questions": global_idx}


def merge_parsed_documents(documents: list[dict]) -> dict:
    """合并多个已解析文档，并重排章节 id 与全局题号。"""
    if not documents:
        return {"intro_html": "", "parts": [], "total_questions": 0}

    intro_html = "\n".join(doc["intro_html"] for doc in documents if doc.get("intro_html"))
    parts: list[dict] = []
    appendices: list[dict] = []

    for idx, doc in enumerate(documents):
        for part in doc["parts"]:
            if idx == 0 and part.get("title", "").startswith("附录"):
                appendices.append(part)
            else:
                parts.append(part)
    parts.extend(appendices)

    total_questions = 0
    for part_idx, part in enumerate(parts):
        part["id"] = f"part-{part_idx}"
        for question in part["questions"]:
            total_questions += 1
            question["global_idx"] = total_questions

    return {"intro_html": intro_html, "parts": parts, "total_questions": total_questions}


def resolve_input_file(value: str) -> Path:
    input_file = Path(value)
    if not input_file.exists():
        input_file = DESKTOP / value

    if not input_file.exists():
        raise SystemExit(f"找不到源文件: {input_file}")

    return input_file


def main():
    parser = argparse.ArgumentParser(description="从面试题 Markdown 生成可视化 HTML")
    parser.add_argument("--input", "-i", default=None, help="输入 Markdown 文件；不传时默认合并主库和补充面经")
    parser.add_argument("--extra-input", action="append", default=[], help="追加合并的 Markdown 文件，可重复传入")
    parser.add_argument("--output", "-o", default=str(OUT_FILE_ASCII), help="输出 HTML 文件")
    parser.add_argument("--also-output", default=str(DESKTOP / "测开面试_通用版_含答案.html"), help="额外输出 HTML 文件")
    parser.add_argument("--index-output", default=str(OUT_FILE_INDEX), help="GitHub Pages 默认入口")
    parser.add_argument("--title", default="测开面试题库（通用版）", help="HTML 标题")
    parser.add_argument("--sidebar-title", default="测开面试题库", help="侧边栏标题")
    args = parser.parse_args()

    if args.input:
        input_files = [resolve_input_file(args.input)]
    else:
        input_files = [MD_FILE] + [p for p in DEFAULT_EXTRA_MD_FILES if p.exists()]
    input_files.extend(resolve_input_file(value) for value in args.extra_input)

    documents = [parse_md(path.read_text(encoding="utf-8-sig")) for path in input_files]
    data = merge_parsed_documents(documents)

    # Load Template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    # Register filters/functions
    env.filters['attr_escape'] = attr_escape
    env.filters['inline_md'] = inline_md
    
    template = env.get_template("base.html")

    # Load Assets
    css_content = (ASSETS_DIR / "style.css").read_text(encoding="utf-8")
    js_content = (ASSETS_DIR / "script.js").read_text(encoding="utf-8")

    html_out = template.render(
        page_title=args.title,
        sidebar_title=args.sidebar_title,
        parts=data["parts"],
        total_questions=data["total_questions"],
        intro_html=data["intro_html"],
        css_content=css_content,
        js_content=js_content
    )
    html_out = "\n".join(line.rstrip() for line in html_out.splitlines()) + "\n"

    Path(args.output).write_text(html_out, encoding="utf-8")
    if args.also_output:
        Path(args.also_output).write_text(html_out, encoding="utf-8")
    if args.index_output:
        Path(args.index_output).write_text(html_out, encoding="utf-8")

    print(f"已生成: {args.output}")
    print("源文件: " + " + ".join(path.name for path in input_files))
    print(f"章节数: {len(data['parts'])}, 题目数: {data['total_questions']}")


if __name__ == "__main__":
    main()
