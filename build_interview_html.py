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
    lines = content.splitlines(keepends=True)
    intro_lines: list[str] = []
    parts: list[dict] = []
    current_part: dict | None = None
    current_q: dict | None = None
    answer_buf: list[str] = []
    in_answer = False
    global_idx = 0

    def finish_question():
        nonlocal current_q, answer_buf, in_answer, global_idx
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
        in_answer = False

    def finish_part():
        nonlocal current_part
        finish_question()
        if current_part is not None:
            parts.append(current_part)
        current_part = None

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")

        if line.startswith("# ") and not line.startswith("## "):
            finish_part()
            title = line[2:].strip()
            if title == "测开面试题库（含答案版）":
                i += 1
                continue
            current_part = {
                "id": f"part-{len(parts)}",
                "title": title,
                "questions": [],
            }
            i += 1
            continue

        if line.startswith("## "):
            finish_question()
            qtitle = line[3:].strip()
            is_scenario = qtitle.startswith("场景")
            current_q = {
                "type": "scenario" if is_scenario else "question",
                "title": qtitle,
                "problem_text": "",
                "answer_html": "",
                "search_text": qtitle,
            }
            i += 1
            continue

        if current_part is None:
            if line.strip() and not line.strip() == "---":
                intro_lines.append(line)
            i += 1
            continue

        if current_q is None:
            if "freeform" not in current_part:
                current_part["freeform"] = []
            current_part["freeform"].append(raw)
            i += 1
            continue

        m_prob_only = re.match(r"^\*\*问题\*\*[：:]\s*(.*)$", line)
        if m_prob_only:
            current_q["problem_text"] = m_prob_only.group(1).strip()
            i += 1
            continue

        if re.match(r"^\*\*答\*\*[：:]", line):
            in_answer = True
            rest = re.sub(r"^\*\*答\*\*[：:]\s*", "", line)
            if rest.strip():
                answer_buf.append(rest)
            i += 1
            continue

        if in_answer or current_q is not None:
            if line.strip() == "---":
                finish_question()
                i += 1
                continue
            if in_answer or (current_q and not current_q.get("answer_html")):
                in_answer = True
                answer_buf.append(raw)
            i += 1
            continue

        i += 1

    finish_part()

    intro_html = ""
    if intro_lines:
        buf = [l.rstrip("\n") for l in intro_lines if l.strip() and l.strip() != "---"]
        items = []
        for l in buf:
            if l.startswith(">"):
                items.append(l.lstrip("> ").strip())
        if items:
            intro_html = "".join(f"<p>{inline_md(x)}</p>" for x in items)

    for p in parts:
        if p.get("freeform"):
            p["freeform_html"] = block_md([l.rstrip("\n") + "\n" for l in p["freeform"]])
            del p["freeform"]

    return {"intro_html": intro_html, "parts": parts, "total_questions": global_idx}


def main():
    parser = argparse.ArgumentParser(description="从面试题 Markdown 生成可视化 HTML")
    parser.add_argument("--input", "-i", default=str(MD_FILE), help="输入 Markdown 文件")
    parser.add_argument("--output", "-o", default=str(OUT_FILE_ASCII), help="输出 HTML 文件")
    parser.add_argument("--also-output", default=str(DESKTOP / "测开面试_通用版_含答案.html"), help="额外输出 HTML 文件")
    parser.add_argument("--index-output", default=str(OUT_FILE_INDEX), help="GitHub Pages 默认入口")
    parser.add_argument("--title", default="测开面试题库（通用版）", help="HTML 标题")
    parser.add_argument("--sidebar-title", default="测开面试题库", help="侧边栏标题")
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        input_file = DESKTOP / args.input

    if not input_file.exists():
        raise SystemExit(f"找不到源文件: {input_file}")

    content = input_file.read_text(encoding="utf-8")
    data = parse_md(content)

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

    Path(args.output).write_text(html_out, encoding="utf-8")
    if args.also_output:
        Path(args.also_output).write_text(html_out, encoding="utf-8")
    if args.index_output:
        Path(args.index_output).write_text(html_out, encoding="utf-8")

    print(f"已生成: {args.output}")
    print(f"章节数: {len(data['parts'])}, 题目数: {data['total_questions']}")


if __name__ == "__main__":
    main()
