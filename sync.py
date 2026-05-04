"""
Sync GitHub starred repos and generate categorized README.
Usage: GH_TOKEN=xxx python sync.py
"""
import json
import subprocess
import sys
from datetime import datetime
from collections import defaultdict

# ── 分类规则 ──────────────────────────────────────────────────
# 顺序很重要！更具体的分类放前面，Agent 放最后兜底
CATEGORIES = [
    {
        "name": "📝 公众号 / 内容创作",
        "keywords": [
            "wechat", "公众号", "weixin", "social-auto-upload",
            "content-creation", "article", "blog", "markdown-editor",
            "md2wechat", "neurapress", "humanizer", "x-article-publisher",
            "xiaohongshu", "bilibili", "tiktok", "youtube",
            "social-media", "publishing", "autoclip"
        ],
        "topics": [
            "wechat", "content-creation", "social-media", "blog",
            "markdown", "xiaohongshu", "bilibili"
        ],
    },
    {
        "name": "🎨 设计 / 原型",
        "keywords": [
            "design-system", "design-systems", "prototype", "figma",
            "ui-design", "slides", "presentation", "ppt",
            "infographic", "illustration", "huashu",
            "open-design", "open-codesign", "architecture-diagram",
            "frontend-slides", "html-ppt"
        ],
        "topics": [
            "design", "figma", "ui", "slides", "presentation",
            "design-system", "prototype"
        ],
    },
    {
        "name": "🎬 视频 / 多媒体",
        "keywords": [
            "video", "remotion", "hyperframes", "whisper", "audio",
            "music", "subtitle", "caption", "ffmpeg", "tts",
            "speech", "voice", "autoclip", "clicky", "video-use",
            "flycut-caption"
        ],
        "topics": [
            "video", "audio", "music", "speech", "whisper", "remotion"
        ],
    },
    {
        "name": "📄 文档 / 知识管理",
        "keywords": [
            "pdf", "zotero", "obsidian", "knowledge", "wiki",
            "document", "mineral", "mineru", "graphify",
            "claudian", "qmd", "search-engine", "rag",
            "opendataloader", "better-notes", "pdf2zh", "pdf-translate"
        ],
        "topics": [
            "obsidian", "zotero", "pdf", "knowledge-graph",
            "note-taking", "wiki", "rag"
        ],
    },
    {
        "name": "🔧 开发工具",
        "keywords": [
            "cli", "browser", "devtools", "mcp", "scrapling",
            "scraping", "crawler", "firecrawl", "proxy",
            "opencli", "debug", "chrome-devtools", "bb-browser",
            "lossless-claw", "cli-proxy", "ghostty", "opencli"
        ],
        "topics": [
            "cli", "browser", "mcp", "devtools", "scraping",
            "api", "debug"
        ],
    },
    {
        "name": "📖 学习 / 方法论",
        "keywords": [
            "english-level", "methodology", "entrepreneur",
            "startup", "opc-methodology", "notebooklm",
            "awesome-notebooklm"
        ],
        "topics": [
            "learning", "awesome-list", "tutorial", "guide",
            "startup", "entrepreneurship"
        ],
    },
    {
        "name": "🤖 Agent / AI 技能框架",
        "keywords": [
            "agent", "skill", "claude-code", "openclaw", "claw-code",
            "cursor", "copilot", "codex", "hermes-agent", "superpowers",
            "agency-agent", "opencode", "gemini-cli", "soul",
            "pua", "khazix-skills", "baoyu-skills", "gstack",
            "gbrain", "agency-agents", "karpathy-skills",
            "everything-claude-code", "awesome-openclaw",
            "web-access", "claude-mem", "cc-switch", "last30days",
            "agency-agent", "superisland", "codeisland", "openless"
        ],
        "topics": [
            "claude-code", "openclaw", "hermes-agent", "ai-agent",
            "cursor", "copilot", "codex", "ai-skills", "agents"
        ],
    },
]


def fetch_all_starred():
    """通过 gh CLI 获取所有 starred repos（GraphQL 分页）"""
    repos = []
    cursor = None
    while True:
        after_clause = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          viewer {{
            starredRepositories(first: 100{after_clause}, orderBy: {{field: STARRED_AT, direction: DESC}}) {{
              pageInfo {{ hasNextPage endCursor }}
              edges {{
                starredAt
                node {{
                  nameWithOwner
                  description
                  url
                  stargazerCount
                  primaryLanguage {{ name }}
                  repositoryTopics(first: 20) {{ nodes {{ topic {{ name }} }} }}
                }}
              }}
            }}
          }}
        }}
        """
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(result.stdout)
        starred = data["data"]["viewer"]["starredRepositories"]
        for edge in starred["edges"]:
            node = edge["node"]
            repos.append({
                "name": node["nameWithOwner"],
                "description": node.get("description") or "",
                "url": node["url"],
                "stars": node["stargazerCount"],
                "language": (node.get("primaryLanguage") or {}).get("name", ""),
                "topics": [t["topic"]["name"] for t in node["repositoryTopics"]["nodes"]],
                "starred_at": edge["starredAt"],
            })
        if not starred["pageInfo"]["hasNextPage"]:
            break
        cursor = starred["pageInfo"]["endCursor"]
    return repos


def categorize(repo):
    """根据仓库名精确匹配 > topics > 关键词"""
    name_lower = repo["name"].lower()
    desc_lower = repo["description"].lower()
    topics_lower = [t.lower() for t in repo["topics"]]

    for cat in CATEGORIES:
        # Topics 匹配（最可靠）
        for t in cat.get("topics", []):
            if t in topics_lower:
                return cat["name"]
        # 仓库名精确匹配（owner/repo 格式）
        for kw in cat.get("keywords", []):
            if kw in name_lower:
                return cat["name"]

    # 兜底：描述关键词（仅对未被上面匹配的）
    for cat in CATEGORIES:
        for kw in cat.get("keywords", []):
            if kw in desc_lower:
                return cat["name"]

    return "📦 其他"


def load_overrides():
    """加载手动覆盖分类（如果存在）"""
    try:
        with open("overrides.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def generate_readme(categorized, total):
    """生成 README.md"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# ⭐ 我的 GitHub Star 收藏",
        "",
        f"> {total} 个仓库 · 每 6 小时自动同步 · 最后更新：{now}",
        "> ",
        "> 想手动指定分类？编辑 [`overrides.json`](overrides.json) 即可覆盖自动分类。",
        "",
        "---",
        "",
    ]

    # 按定义顺序输出
    category_order = [c["name"] for c in CATEGORIES] + ["📦 其他"]
    for cat_name in category_order:
        repos = categorized.get(cat_name, [])
        if not repos:
            continue
        lines.append(f"## {cat_name}")
        lines.append("")
        lines.append("| 仓库 | ⭐ | 说明 |")
        lines.append("|------|-----|------|")
        for r in sorted(repos, key=lambda x: x["stars"], reverse=True):
            desc = r["description"][:60] + "..." if len(r["description"]) > 60 else r["description"]
            desc = desc.replace("|", "\\|")
            lines.append(f"| [{r['name']}]({r['url']}) | {r['stars']:,} | {desc} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*自动同步 by [sync-stars workflow] · [lilong-98](https://github.com/lilong-98)*")
    return "\n".join(lines) + "\n"


def main():
    print("⭐ Fetching starred repos...")
    repos = fetch_all_starred()
    print(f"   Found {len(repos)} repos")

    # 加载手动覆盖
    overrides = load_overrides()

    # 分类
    categorized = defaultdict(list)
    for repo in repos:
        # 优先用手动覆盖
        if repo["name"] in overrides:
            cat = overrides[repo["name"]]
        else:
            cat = categorize(repo)
        categorized[cat].append(repo)

    # 生成 README
    readme = generate_readme(categorized, len(repos))
    with open("README.md", "w") as f:
        f.write(readme)

    # 统计
    print("\n📊 分类统计：")
    for cat in [c["name"] for c in CATEGORIES] + ["📦 其他"]:
        count = len(categorized.get(cat, []))
        if count:
            print(f"   {cat}: {count}")

    print(f"\n✅ README.md updated ({len(repos)} repos)")


if __name__ == "__main__":
    main()
