#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从面试题 Markdown 生成可视化 HTML（只读 MD，不修改源文件）"""

import html
import re
import json
import argparse
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent
DEFAULT_ORIGINAL_DIR = DESKTOP
MD_FILE = DEFAULT_ORIGINAL_DIR / "测开面试_通用版_含答案.md"
OUT_FILE = DEFAULT_ORIGINAL_DIR / "测开面试_通用版_含答案.html"
OUT_FILE_ASCII = DEFAULT_ORIGINAL_DIR / "interview-qa-general.html"  # 英文文件名，避免部分环境无法打开
OUT_FILE_INDEX = DEFAULT_ORIGINAL_DIR / "index.html"  # GitHub Pages 默认入口


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

        # 无序列表（含缩进子项）
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

        # 有序列表（含缩进子项）
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

        # **问题**： / **答**： 行内标签（场景题问题行可能带内容）
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

    def finish_question():
        nonlocal current_q, answer_buf, in_answer
        if current_q is not None:
            body = block_md(answer_buf) if answer_buf else ""
            current_q["answer_html"] = body
            current_q["search_text"] = (
                current_q.get("title", "")
                + " "
                + current_q.get("problem_text", "")
                + " "
                + "\n".join(answer_buf)
            )
            if current_part is not None:
                current_part["items"].append(current_q)
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

        # 一级标题：部分
        if line.startswith("# ") and not line.startswith("## "):
            finish_part()
            title = line[2:].strip()
            if title == "测开面试题库（含答案版）":
                i += 1
                continue
            slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")[:60]
            current_part = {
                "id": f"part-{len(parts)}",
                "slug": slug or f"part-{len(parts)}",
                "title": title,
                "items": [],
                "is_appendix": title.startswith("附录"),
            }
            i += 1
            continue

        # 二级标题：题目
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

        # 尚未进入任何部分：收集 intro
        if current_part is None:
            if line.strip() and not line.strip() == "---":
                intro_lines.append(line)
            i += 1
            continue

        # 附录等特殊：无 ## 的纯列表内容
        if current_q is None:
            # 累积为 part 的 freeform 内容
            if "freeform" not in current_part:
                current_part["freeform"] = []
            current_part["freeform"].append(raw)
            i += 1
            continue

        # **问题**： 单独一行（场景题）
        m_prob_only = re.match(r"^\*\*问题\*\*[：:]\s*(.*)$", line)
        if m_prob_only:
            current_q["problem_text"] = m_prob_only.group(1).strip()
            i += 1
            continue

        # **答**： 开始答案
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
            intro_html = "<div class=\"intro\">" + "".join(
                f"<p>{inline_md(x)}</p>" for x in items
            ) + "</div>"

    # 处理 appendix freeform
    for p in parts:
        if p.get("freeform"):
            p["freeform_html"] = block_md([l.rstrip("\n") + "\n" for l in p["freeform"]])
            del p["freeform"]

    return {"intro_html": intro_html, "parts": parts}


def render_question_card(q: dict, global_idx: int) -> str:
    qtype = q.get("type", "question")
    cls = "card scenario" if qtype == "scenario" else "card"
    title = escape(q["title"])
    problem = q.get("problem_text", "")
    answer = q.get("answer_html", "")

    problem_html = ""
    if problem:
        problem_html = f"""
        <div class="problem-block">
          <span class="badge badge-problem">问题</span>
          <p>{inline_md(problem)}</p>
        </div>"""

    return f"""
    <article class="{cls}" data-idx="{global_idx}" data-search="{attr_escape(q.get('search_text', '')[:500])}">
      <header class="card-header" role="button" tabindex="0" aria-expanded="false">
        <span class="card-index">#{global_idx}</span>
        <h3 class="card-title">{title}</h3>
        <button type="button" class="toggle-btn" aria-label="展开答案">展开</button>
      </header>
      <div class="card-body" hidden>
        {problem_html}
        <div class="answer-block">
          <span class="badge badge-answer">答</span>
          <div class="answer-content">{answer}</div>
        </div>
      </div>
    </article>"""


def render_part(part: dict, start_idx: int) -> tuple[str, int]:
    idx = start_idx
    cards = []
    for q in part.get("items", []):
        idx += 1
        cards.append(render_question_card(q, idx))

    freeform = part.get("freeform_html", "")
    freeform_block = f'<div class="freeform-content">{freeform}</div>' if freeform else ""

    nav_title = escape(part["title"])
    return (
        f"""
    <section class="part-section" id="{part['id']}" data-part="{escape(part['title'])}">
      <h2 class="part-title">{nav_title}</h2>
      <p class="part-meta">共 {len(part.get('items', []))} 题</p>
      {freeform_block}
      <div class="cards-grid">
        {"".join(cards)}
      </div>
    </section>""",
        idx,
    )


CSS = r"""
:root {
  --bg: #f6f7f9;
  --surface: #ffffff;
  --text: #1a1d21;
  --text-muted: #5c6370;
  --border: #e2e5eb;
  --accent: #2563eb;
  --accent-soft: #eff6ff;
  --answer-bg: #f0fdf4;
  --answer-border: #86efac;
  --scenario-accent: #d97706;
  --scenario-soft: #fffbeb;
  --sidebar-w: 280px;
  --header-h: 56px;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
[data-theme="dark"] {
  --bg: #0f1117;
  --surface: #1a1d24;
  --text: #e8eaed;
  --text-muted: #9aa0a6;
  --border: #2d323c;
  --accent: #60a5fa;
  --accent-soft: #1e3a5f;
  --answer-bg: #142819;
  --answer-border: #166534;
  --scenario-soft: #292218;
  --shadow: 0 1px 3px rgba(0,0,0,.4);
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-size: 16px;
  line-height: 1.7;
}
.app { display: flex; min-height: 100vh; }
.sidebar {
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: var(--sidebar-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  z-index: 100;
  transition: transform .25s;
}
.sidebar-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0;
  background: var(--surface);
}
.sidebar-header h1 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
}
.sidebar-header .sub { font-size: .75rem; color: var(--text-muted); margin-top: .25rem; }
.nav-list { list-style: none; margin: 0; padding: .5rem 0 2rem; }
.nav-list a {
  display: block;
  padding: .45rem 1.25rem;
  color: var(--text-muted);
  text-decoration: none;
  font-size: .85rem;
  border-left: 3px solid transparent;
  transition: all .15s;
}
.nav-list a:hover { color: var(--accent); background: var(--accent-soft); }
.nav-list a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}
.main-wrap {
  margin-left: var(--sidebar-w);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  position: sticky;
  top: 0;
  z-index: 90;
  height: var(--header-h);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: 0 1.5rem;
  box-shadow: var(--shadow);
}
.menu-btn {
  display: none;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .35rem .6rem;
  cursor: pointer;
  color: var(--text);
}
.search-wrap { flex: 1; max-width: 420px; position: relative; }
.search-wrap input {
  width: 100%;
  padding: .5rem 1rem .5rem 2.25rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: .9rem;
}
.search-wrap input:focus {
  outline: 2px solid var(--accent);
  border-color: transparent;
}
.search-icon {
  position: absolute;
  left: .75rem;
  top: 50%;
  transform: translateY(-50%);
  opacity: .5;
  font-size: .9rem;
}
.search-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.search-nav button {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: .85rem;
  cursor: pointer;
  line-height: 1;
}
.search-nav button:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}
.search-nav button:disabled {
  opacity: .35;
  cursor: not-allowed;
}
.search-stats { font-size: .8rem; color: var(--text-muted); white-space: nowrap; min-width: 4.5rem; }
.card.search-current {
  box-shadow: 0 0 0 2px var(--accent), var(--shadow);
  border-color: var(--accent) !important;
}
.card.search-current .card-header { background: var(--accent-soft); }
.toolbar { display: flex; gap: .5rem; flex-wrap: wrap; }
.toolbar button {
  padding: .4rem .75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: .8rem;
  cursor: pointer;
}
.toolbar button:hover { border-color: var(--accent); color: var(--accent); }
.content {
  padding: 1.5rem 2rem 4rem;
  max-width: 960px;
}
.intro {
  background: var(--accent-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  margin-bottom: 2rem;
}
.intro p { margin: .35rem 0; font-size: .9rem; color: var(--text-muted); }
.part-section { margin-bottom: 3rem; scroll-margin-top: calc(var(--header-h) + 12px); }
.part-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 .25rem;
  padding-bottom: .5rem;
  border-bottom: 2px solid var(--accent);
}
.part-meta { font-size: .85rem; color: var(--text-muted); margin: 0 0 1.25rem; }
.cards-grid { display: flex; flex-direction: column; gap: .75rem; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border-left: 4px solid var(--accent);
  overflow: hidden;
}
.card.scenario { border-left-color: var(--scenario-accent); }
.card.hidden-by-search { display: none !important; }
.card-header {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  padding: 1rem 1.25rem;
  cursor: pointer;
  user-select: none;
}
.card-header:hover { background: var(--bg); }
.card-index {
  flex-shrink: 0;
  font-size: .75rem;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg);
  padding: .15rem .45rem;
  border-radius: 4px;
}
.card-title {
  flex: 1;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.toggle-btn {
  flex-shrink: 0;
  padding: .25rem .6rem;
  font-size: .75rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg);
  color: var(--text-muted);
  cursor: pointer;
}
.card.expanded .toggle-btn { color: var(--accent); border-color: var(--accent); }
.card-body { padding: 0 1.25rem 1.25rem; border-top: 1px solid var(--border); }
.card-body[hidden] { display: none; }
.problem-block, .problem-inline {
  background: var(--scenario-soft);
  border-radius: 8px;
  padding: .75rem 1rem;
  margin-bottom: 1rem;
}
.problem-block p { margin: .5rem 0 0; }
.answer-block {
  background: var(--answer-bg);
  border: 1px solid var(--answer-border);
  border-radius: 8px;
  padding: 1rem;
}
.badge {
  display: inline-block;
  font-size: .7rem;
  font-weight: 700;
  padding: .15rem .5rem;
  border-radius: 4px;
  margin-bottom: .5rem;
}
.badge-answer { background: #16a34a; color: #fff; }
.badge-problem { background: var(--scenario-accent); color: #fff; }
.answer-content p { margin: .5rem 0; }
.answer-content ul, .answer-content ol { margin: .5rem 0; padding-left: 1.5rem; }
.answer-content li { margin: .25rem 0; }
.point-list {
  list-style: none;
  margin: .5rem 0 .75rem;
  padding: 0;
}
.point-list li {
  padding: .5rem .75rem;
  margin: 0 0 .35rem;
  background: var(--bg);
  border-radius: 6px;
  border-left: 3px solid var(--accent);
  line-height: 1.65;
}
[data-theme="dark"] .point-list li { background: #12151c; }
.freeform-content .point-list li { border-left-color: var(--accent); }
.code-block {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
  overflow-x: auto;
  font-size: .8rem;
  line-height: 1.5;
  margin: .75rem 0;
}
.code-block code { font-family: Consolas, "Courier New", monospace; white-space: pre; }
mark.hl { background: #fef08a; color: #1a1d21; padding: 0 .1em; border-radius: 2px; }
[data-theme="dark"] mark.hl { background: #854d0e; color: #fef08a; }
.freeform-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.freeform-content p, .freeform-content li { font-size: .95rem; }
.back-top {
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  width: 44px; height: 44px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  box-shadow: var(--shadow);
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s;
  z-index: 80;
}
.back-top.visible { opacity: 1; pointer-events: auto; }
.no-results {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted);
  display: none;
}
.no-results.show { display: block; }
  @media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
  .main-wrap { margin-left: 0; }
  .menu-btn { display: block; }
  .content { padding: 1rem; }
  .search-stats { min-width: 3rem; font-size: .75rem; }
}
@media print {
  .sidebar, .topbar, .back-top, .toggle-btn, .menu-btn { display: none !important; }
  .main-wrap { margin-left: 0; }
  .card-body { display: block !important; }
  .card { break-inside: avoid; page-break-inside: avoid; }
}
"""

JS = r"""
(function () {
  const cards = document.querySelectorAll('.card');
  const searchInput = document.getElementById('search');
  const searchStats = document.getElementById('searchStats');
  const searchPrev = document.getElementById('searchPrev');
  const searchNext = document.getElementById('searchNext');
  const noResults = document.getElementById('noResults');
  const navLinks = document.querySelectorAll('.nav-list a');
  const sections = document.querySelectorAll('.part-section');
  const backTop = document.getElementById('backTop');
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.getElementById('menuBtn');
  const themeBtn = document.getElementById('themeBtn');
  const expandAllBtn = document.getElementById('expandAll');
  const collapseAllBtn = document.getElementById('collapseAll');

  let matchCards = [];
  let matchIndex = -1;

  function setExpanded(card, open) {
    const body = card.querySelector('.card-body');
    const header = card.querySelector('.card-header');
    const btn = card.querySelector('.toggle-btn');
    if (!body) return;
    if (open) {
      body.hidden = false;
      card.classList.add('expanded');
      header.setAttribute('aria-expanded', 'true');
      if (btn) btn.textContent = '收起';
    } else {
      body.hidden = true;
      card.classList.remove('expanded');
      header.setAttribute('aria-expanded', 'false');
      if (btn) btn.textContent = '展开';
    }
  }

  cards.forEach(card => {
    const header = card.querySelector('.card-header');
    const btn = card.querySelector('.toggle-btn');
    const toggle = (e) => {
      if (e.target.closest('.toggle-btn')) e.stopPropagation();
      setExpanded(card, card.querySelector('.card-body').hidden);
    };
    header.addEventListener('click', toggle);
    header.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); }
    });
    if (btn) btn.addEventListener('click', e => { e.stopPropagation(); toggle(e); });
  });

  expandAllBtn.addEventListener('click', () => cards.forEach(c => {
    if (!c.classList.contains('hidden-by-search')) setExpanded(c, true);
  }));
  collapseAllBtn.addEventListener('click', () => cards.forEach(c => setExpanded(c, false)));

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function highlightText(el, q) {
    if (!q || q.length < 1) return;
    const walk = (node) => {
      if (node.nodeType === 3) {
        const t = node.textContent;
        const lower = t.toLowerCase();
        const ql = q.toLowerCase();
        const idx = lower.indexOf(ql);
        if (idx >= 0) {
          const span = document.createElement('span');
          span.innerHTML = escapeHtml(t.slice(0, idx)) + '<mark class="hl">' + escapeHtml(t.slice(idx, idx + q.length)) + '</mark>' + escapeHtml(t.slice(idx + q.length));
          node.parentNode.replaceChild(span, node);
        }
      } else if (node.nodeType === 1 && !['SCRIPT','STYLE','MARK'].includes(node.tagName)) {
        Array.from(node.childNodes).forEach(walk);
      }
    };
    walk(el);
  }

  function restoreHighlight(el) {
    if (el && el.dataset.originalHtml) {
      el.innerHTML = el.dataset.originalHtml;
    }
  }

  function applyHighlights(card, q) {
    const title = card.querySelector('.card-title');
    const content = card.querySelector('.answer-content');
    [title, content].forEach(el => {
      if (!el) return;
      if (!el.dataset.originalHtml) {
        el.dataset.originalHtml = el.innerHTML;
      }
      el.innerHTML = el.dataset.originalHtml;
      if (q) highlightText(el, q);
    });
  }

  function updateSearchNavButtons() {
    const hasQuery = searchInput.value.trim().length > 0;
    const hasMatches = matchCards.length > 0;
    searchPrev.disabled = !hasQuery || !hasMatches;
    searchNext.disabled = !hasQuery || !hasMatches;
  }

  function clearCurrentMatch() {
    cards.forEach(c => c.classList.remove('search-current'));
    matchIndex = -1;
  }

  function goToMatch(index) {
    if (!matchCards.length) {
      clearCurrentMatch();
      updateSearchNavButtons();
      return;
    }
    if (index < 0) index = matchCards.length - 1;
    if (index >= matchCards.length) index = 0;
    matchIndex = index;
    cards.forEach(c => c.classList.remove('search-current'));
    const card = matchCards[matchIndex];
    card.classList.add('search-current');
    setExpanded(card, true);
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    searchStats.textContent = (matchIndex + 1) + ' / ' + matchCards.length;
    updateSearchNavButtons();
  }

  function runSearch(jumpToFirst) {
    const q = searchInput.value.trim();
    matchCards = [];
    clearCurrentMatch();
    let visible = 0;

    cards.forEach(card => {
      const text = (card.getAttribute('data-search') || '') + ' ' + (card.querySelector('.card-title')?.textContent || '') + ' ' + (card.querySelector('.answer-content')?.textContent || '');
      const match = !q || text.toLowerCase().includes(q.toLowerCase());
      card.classList.toggle('hidden-by-search', !match);
      if (match) {
        visible++;
        matchCards.push(card);
        if (q) setExpanded(card, true);
      }
      applyHighlights(card, q);
    });

    sections.forEach(sec => {
      const any = sec.querySelector('.card:not(.hidden-by-search)');
      sec.style.display = any || !q ? '' : 'none';
    });

    noResults.classList.toggle('show', q && visible === 0);

    if (!q) {
      searchStats.textContent = '';
      updateSearchNavButtons();
      return;
    }

    if (visible === 0) {
      searchStats.textContent = '无匹配';
      updateSearchNavButtons();
      return;
    }

    if (jumpToFirst !== false) {
      goToMatch(0);
    } else if (matchIndex >= 0 && matchIndex < matchCards.length) {
      goToMatch(matchIndex);
    } else {
      searchStats.textContent = '共 ' + visible + ' 条';
      updateSearchNavButtons();
    }
  }

  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(true), 200);
  });

  searchInput.addEventListener('keydown', (e) => {
    const q = searchInput.value.trim();
    if (!q || !matchCards.length) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) goToMatch(matchIndex - 1);
      else goToMatch(matchIndex < 0 ? 0 : matchIndex + 1);
    }
  });

  searchPrev.addEventListener('click', () => goToMatch(matchIndex - 1));
  searchNext.addEventListener('click', () => goToMatch(matchIndex < 0 ? 0 : matchIndex + 1));

  updateSearchNavButtons();

  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const id = e.target.id;
        navLinks.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === '#' + id);
        });
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  sections.forEach(s => observer.observe(s));

  navLinks.forEach(a => {
    a.addEventListener('click', () => sidebar.classList.remove('open'));
  });
  menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));

  window.addEventListener('scroll', () => {
    backTop.classList.toggle('visible', window.scrollY > 400);
  });
  backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  const saved = localStorage.getItem('interview-theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  themeBtn.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next === 'light' ? '' : 'dark');
    localStorage.setItem('interview-theme', next === 'light' ? '' : 'dark');
    themeBtn.textContent = next === 'dark' ? '浅色' : '深色';
  });
  if (document.documentElement.getAttribute('data-theme') === 'dark') themeBtn.textContent = '浅色';
})();
"""


def build_html(data: dict, page_title: str = "测开面试题库（通用版）", sidebar_title: str = "测开面试题库（通用版）") -> str:
    nav_items = []
    body_parts = []
    global_idx = 0

    for part in data["parts"]:
        nav_items.append(
            f'<li><a href="#{part["id"]}">{escape(part["title"])}</a></li>'
        )
        section_html, global_idx = render_part(part, global_idx)
        body_parts.append(section_html)

    total_q = global_idx
    nav_html = "\n".join(nav_items)
    body_html = "\n".join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(page_title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="app">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <h1>{escape(sidebar_title)}</h1>
        <div class="sub">含答案 · 共 {total_q} 题</div>
      </div>
      <ul class="nav-list">
        {nav_html}
      </ul>
    </aside>
    <div class="main-wrap">
      <header class="topbar">
        <button type="button" class="menu-btn" id="menuBtn" aria-label="菜单">☰</button>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input type="search" id="search" placeholder="搜索题目或答案关键词…" autocomplete="off">
        </div>
        <div class="search-nav" id="searchNav">
          <button type="button" id="searchPrev" disabled title="上一个 (↑)">↑</button>
          <button type="button" id="searchNext" disabled title="下一个 (↓)">↓</button>
        </div>
        <span class="search-stats" id="searchStats"></span>
        <div class="toolbar">
          <button type="button" id="expandAll">全部展开</button>
          <button type="button" id="collapseAll">全部折叠</button>
          <button type="button" id="themeBtn">深色</button>
        </div>
      </header>
      <main class="content">
        {data["intro_html"]}
        {body_html}
        <p class="no-results" id="noResults">未找到匹配内容，请换个关键词试试</p>
      </main>
    </div>
  </div>
  <button type="button" class="back-top" id="backTop" aria-label="回到顶部">↑</button>
  <script>{JS}</script>
</body>
</html>"""


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else DESKTOP / path


def main():
    parser = argparse.ArgumentParser(description="从面试题 Markdown 生成可视化 HTML")
    parser.add_argument("--input", "-i", default=str(MD_FILE), help="输入 Markdown 文件")
    parser.add_argument("--output", "-o", default=str(OUT_FILE_ASCII), help="输出 HTML 文件")
    parser.add_argument("--also-output", default=str(OUT_FILE), help="额外输出 HTML 文件；传空字符串可关闭")
    parser.add_argument("--index-output", default=str(OUT_FILE_INDEX), help="GitHub Pages 默认入口；传空字符串可关闭")
    parser.add_argument("--title", default="测开面试题库（通用版）", help="HTML 标题")
    parser.add_argument("--sidebar-title", default="测开面试题库（通用版）", help="侧边栏标题")
    args = parser.parse_args()

    input_file = resolve_path(args.input)
    output_file = resolve_path(args.output)
    also_output = resolve_path(args.also_output) if args.also_output else None
    index_output = resolve_path(args.index_output) if args.index_output else None

    if not input_file.exists():
        raise SystemExit(f"找不到源文件: {input_file}")
    content = input_file.read_text(encoding="utf-8")
    data = parse_md(content)
    html_out = build_html(data, page_title=args.title, sidebar_title=args.sidebar_title)
    output_file.write_text(html_out, encoding="utf-8")
    if also_output and also_output != output_file:
        also_output.write_text(html_out, encoding="utf-8")
    if index_output and index_output not in {output_file, also_output}:
        index_output.write_text(html_out, encoding="utf-8")
    total = sum(len(p.get("items", [])) for p in data["parts"])
    if also_output and also_output != output_file:
        print(f"已生成: {also_output}")
    if index_output and index_output not in {output_file, also_output}:
        print(f"已生成: {index_output}")
    print(f"已生成: {output_file}")
    print(f"章节数: {len(data['parts'])}, 题目数: {total}")


if __name__ == "__main__":
    main()

