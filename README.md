# 测开面试题库（通用版）

## 文件说明

| 文件 | 说明 |
|------|------|
| `测开面试_通用版.md` | 通用测开 + 通用 AI 产品版题目清单 |
| `测开面试_通用版_含答案.md` | 通用测开 + 通用 AI 产品版含答案 Markdown |
| `interview-qa-general.html` | 可视化 HTML 页面 |
| `index.html` | GitHub Pages 默认入口，内容与可视化页面一致 |
| `build_interview_html.py` | 从本目录 Markdown 重新生成 HTML |

## 使用方式

双击 `interview-qa-general.html` 用 Chrome / Edge 打开。

更新 Markdown 后，在本目录打开终端运行：

```bash
python3 build_interview_html.py
```

脚本默认读取 `测开面试_通用版_含答案.md`，并同步更新：

- `interview-qa-general.html`
- `测开面试_通用版_含答案.html`
- `index.html`

如需临时生成其他 Markdown 文件，可使用现有 `--input` / `--output` 参数：

```bash
python3 build_interview_html.py \
  --input /Users/daiqibin/Downloads/knowledge-test/测开面经.md \
  --output /tmp/mianshi.html \
  --also-output "" \
  --index-output ""
```

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
