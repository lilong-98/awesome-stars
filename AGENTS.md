# awesome-stars

自动把我的 GitHub Star 收藏按分类整理成 README。GitHub Actions 每 6 小时运行 `sync.py`，用仓库 secret `PAT` 拉取 star 列表，重新生成 README.md 并自动提交。

## 开始工作

1. 先 `git pull`：远程每天都有 bot 的自动提交，本地往往落后。
2. 读 `sync.py` 开头的 `CATEGORIES`（分类规则）和 `.github/workflows/sync-stars.yml`（调度）。

## 约定

- README.md 是生成产物，手改会被下一次同步覆盖。要改分类，按以下方式处理：
  - 个别仓库分错：在 `overrides.json` 里指定。
  - 一类仓库分错：改 `CATEGORIES` 的 keywords / topics。更具体的分类排在前面，Agent 类放最后兜底。
- 本地试跑：`GH_TOKEN=$(gh auth token) uv run sync.py`。确认效果后只提交脚本和配置；README 交给 Actions 重新生成，避免和 bot 的提交冲突。
