# 测开面试题库（通用版）

按章节拆分的多页可视化站点：首页 `index.html` 是章节目录，每个技术章节是一个独立页面，放在 `chapters/` 目录下，顶部搜索框支持跨章节全局检索。AI 相关内容已按 `LLM 基础与 Prompt`、`RAG 知识增强`、`AI Agent 自动执行`、`AI 工具生态与能力扩展`、`AI 测试与评测`、`LLMOps 工程化工具` 拆分；5 年测开常见深挖内容补充了 `项目经历与 STAR 回答`、`中间件与微服务排障` 和 `高频短板补强`。

## 文件说明

| 文件 / 目录 | 说明 |
|------|------|
| `index.html` | 首页目录（GitHub Pages 默认入口），列出全部章节并提供全局搜索 |
| `chapters/` | 按技术章节拆分的页面，每章一个 HTML，如 `chapters/pytest.html` |
| `assets/style.css` | 站点样式 |
| `assets/script.js` | 站点交互（折叠、主题、全局搜索、深链跳转） |
| `assets/search-index.json` | 构建产物：全局搜索索引（同时内联进每个页面，便于本地直接打开） |
| `测开面试_通用版.md` | 通用测开 + 通用 AI 产品版题目清单 |
| `测开面试_通用版_含答案.md` | 通用测开 + 通用 AI 产品版含答案 Markdown |
| `测开面经.md` | 补充面经 Markdown，默认会合并到站点 |
| `sources/测试开发面试题解答/` | 深度专题源文件，默认按技术主题融合进站点 |
| `sources/测试开发面试题解答/测试开发与AI_Agent面试题汇总.md` | 题干与扩展问题来源；构建时会把原“追问”拆成独立题卡，并从对应主问题答案中生成答题要点 |
| `sources/测试开发面试题解答/18-项目经历_STAR.md` | 项目经历、负责人能力、线上复盘和 AI/RAG 项目讲法 |
| `sources/测试开发面试题解答/19-中间件与微服务排障.md` | Redis、MQ、网关、Kubernetes、配置中心、熔断降级等微服务排障题 |
| `sources/测试开发面试题解答/20-高频短板补强.md` | pytest、CI/CD、Allure、质量门禁、flaky 用例等短答案补强 |
| `去重合并报告.md` | 构建时输出的保守去重记录 |
| `build_interview_html.py` | 纯 Python 标准库构建脚本，无需安装第三方依赖 |

## 使用方式

双击 `index.html` 用 Chrome / Edge 打开，点击任一章节进入，或在顶部搜索框跨章节检索。

更新 Markdown 后，在本目录打开终端运行：

```bash
py build_interview_html.py
```

脚本默认合并读取 `测开面试_通用版_含答案.md`、`测开面经.md` 和 `sources/测试开发面试题解答/` 下的深度专题文件，按技术主题归类并做保守去重。汇总文件里的原“追问”不会挂在主问题下面，而是会拆成独立扩展题卡，进入搜索、收藏、随机题和掌握标记流程。页面展示编号会按每个技术章节重新连续编号为 `Q001`、`Q002`、`Q003`，原始编号仅保留在搜索文本和标题提示中，方便追溯但不干扰阅读。然后同步更新：

- `index.html`（首页目录）
- `chapters/*.html`（每个章节一个页面，构建时会重建该目录）
- `assets/search-index.json`（全局搜索索引）
- `去重合并报告.md`

可选参数：

- `--input` / `-i`：只用指定的 Markdown 文件（显式传入时不会自动合并默认补充源）。
- `--extra-input`：在默认源之外追加其他文件，可重复传入。
- `--index-output` / `--chapters-dir`：自定义首页与章节目录输出位置。
- `--title` / `--sidebar-title`：自定义标题。

## 上传 GitHub 后预览

推荐用 GitHub Pages，而不是直接点 GitHub 文件预览。

1. 把本文件夹内的全部文件上传到仓库根目录，尤其要包含 `index.html` 和整个 `chapters/` 目录。
2. 进入仓库 `Settings -> Pages`。
3. `Build and deployment` 选择 `Deploy from a branch`。
4. Branch 选择 `main`，目录选择 `/ (root)`，保存。
5. 等待 Pages 部署完成后，用 GitHub 给出的地址访问。

本仓库的 Pages 入口是根目录下的 `index.html`。章节页面通过相对路径链接，CSS / JS / 搜索索引均已内联进每个 HTML，所以本地双击和 Pages 上都能正常工作。

最终访问地址通常类似：

```text
https://你的用户名.github.io/test_knowledge/
```
