# 测开面试题库（通用版）

## 文件说明

| 文件 | 说明 |
|------|------|
| `测开面试_通用版.md` | 通用测开 + 通用 AI 产品版题目清单 |
| `测开面试_通用版_含答案.md` | 通用测开 + 通用 AI 产品版含答案 Markdown |
| `测开面经.md` | 补充面经 Markdown，默认会合并到可视化页面 |
| `sources/测试开发面试题解答/` | 深度专题源文件，默认按技术主题融合进页面 |
| `去重合并报告.md` | 构建时输出的保守去重记录 |
| `interview-qa-general.html` | 可视化 HTML 页面 |
| `index.html` | GitHub Pages 默认入口，内容与可视化页面一致 |
| `build_interview_html.py` | 纯 Python 标准库构建脚本，无需安装第三方依赖 |

## 使用方式

双击 `interview-qa-general.html` 用 Chrome / Edge 打开。

更新 Markdown 后，在本目录打开终端运行：

```bash
py build_interview_html.py
```

脚本默认合并读取 `测开面试_通用版_含答案.md`、`测开面经.md` 和 `sources/测试开发面试题解答/` 下的深度专题文件，按技术主题归类并做保守去重，然后同步更新：

- `interview-qa-general.html`
- `测开面试_通用版_含答案.html`
- `index.html`
- `去重合并报告.md`

如需单独生成某个 Markdown 文件，可使用 `--input` / `--output` 参数。显式传入 `--input` 时不会自动合并默认补充源：

```bash
py build_interview_html.py \
  --input 测开面经.md \
  --output /tmp/mianshi.html \
  --also-output "" \
  --index-output "" \
  --report-output ""
```

如需在默认源之外继续追加其他文件，可重复传入 `--extra-input`。

## 上传 GitHub 后预览

推荐用 GitHub Pages，而不是直接点 GitHub 文件预览。

1. 新建一个 GitHub 仓库，例如 `test-dev-interview-general`。
2. 把本文件夹内的全部文件上传到仓库根目录，尤其要包含 `index.html`。
3. 进入仓库 `Settings -> Pages`。
4. `Build and deployment` 选择 `Deploy from a branch`。
5. Branch 选择 `main`，目录选择 `/root`，保存。
6. 等待 Pages 部署完成后，用 GitHub 给出的地址访问。

本仓库的 Pages 入口是根目录下的 `index.html`，因此只要提交并推送最新生成的 `index.html`，Pages 会自动展示最新页面。

最终访问地址通常类似：

```text
https://你的用户名.github.io/test-dev-interview-general/
```

`index.html` 是公开预览入口；`interview-qa-general.html` 保留给本地双击打开。
