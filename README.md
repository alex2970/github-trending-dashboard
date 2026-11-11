# GitHub 热门项目日报

每天自动抓取 GitHub 上各分类的热门新项目，每类 10 个，打开网页就能看。

## 在线查看

https://alex2970.github.io/github-trending-dashboard/

## 分类

| 分类 | 内容 |
| --- | --- |
| 🔥 总榜 | 近 30 天创建、最受关注的新项目 |
| 📋 办公效率 | 笔记、待办、文档与效率工具 |
| 🛠️ 开发工具 | 开发者工具、CLI 与工程效率 |
| 💻 系统工具 | 操作系统、系统工具与终端 |
| 🏠 生活日常 | 智能家居、健康、理财与生活 |
| 🤖 AI 应用 | 大模型、智能体与 AI 应用 |
| 📚 学习教育 | 教程、课程与学习资源 |
| 🎬 媒体娱乐 | 视频、音乐、直播与游戏 |
| 🔒 安全隐私 | 安全、隐私与加密工具 |

## 更新机制

- 每天 10:00（北京时间）由 GitHub Actions 自动运行 `scripts/fetch_trending.py`，用 GitHub Search API 按“近 60 天创建、按 stars 排序”取每类前 10，不足时放宽到 180 天；跨分类去重。
- 数据按日期存为 `data/YYYY-MM-DD.json`，`data/latest.json` 永远是最新一天，`data/index.json` 是日期清单；页面顶部的日期下拉框可以翻看历史。
- 手动立即更新：仓库 Actions 页 → “每日更新热门数据” → Run workflow。

## 本地运行

```bash
python3 scripts/fetch_trending.py   # 生成今日 data/，有 GITHUB_TOKEN 时额度更高
```

## 说明

- 数据来源：GitHub Search API（公开接口），只读，不写任何仓库内容。
- 部署：GitHub Pages（免费），全部代码与数据都在本仓库，不依赖任何第三方服务器。
