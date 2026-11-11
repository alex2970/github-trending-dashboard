#!/usr/bin/env python3

"""每日抓取 GitHub 热门项目，按分类存成 data/YYYY-MM-DD.json。


数据源：GitHub Search API（公开接口）。

- 有 GITHUB_TOKEN 时走认证额度（搜索 30 次/分钟），无 token 时 10 次/分钟，脚本自带间隔。

- “热门”口径：近 60 天内创建、按 stars 排序的前 10；不足 10 个时放宽到 180 天。

  总榜：近 30 天创建且 stars > 300，按 stars 排序的前 10。

- 输出：data/<日期>.json、data/latest.json、data/index.json（日期清单）。

- 日期一律按北京时间（Asia/Shanghai）。

- 简介翻译：英文 description 翻成中文存 description_zh，翻译结果缓存在
  data/translations.json（按原文去重，缺的才新翻），失败时留空、下次再试。
"""

import json

import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


CST = ZoneInfo("Asia/Shanghai") if ZoneInfo else timezone(timedelta(hours=8))
API = "https://api.github.com/search/repositories"

CATEGORIES = [
    {"id": "all", "name": "总榜", "icon": "🔥", "desc": "近 30 天创建、最受关注的新项目",
     "queries": ["stars:>300"]},

    {"id": "office", "name": "办公效率", "icon": "📋", "desc": "笔记、待办、文档与效率工具",
     "topics": ["productivity", "notes", "todo", "kanban", "markdown"]},

    {"id": "devtools", "name": "开发工具", "icon": "🛠️", "desc": "开发者工具、CLI 与工程效率",
     "topics": ["developer-tools", "cli", "devops", "git", "testing"]},

    {"id": "system", "name": "系统工具", "icon": "💻", "desc": "操作系统、系统工具与终端",
     "topics": ["linux", "operating-system", "system", "shell", "terminal"]},

    {"id": "life", "name": "生活日常", "icon": "🏠", "desc": "智能家居、健康、理财与生活",
     "topics": ["self-hosted", "home-automation", "health", "finance", "recipes"]},

    {"id": "ai", "name": "AI 应用", "icon": "🤖", "desc": "大模型、智能体与 AI 应用",
     "topics": ["llm", "artificial-intelligence", "ai", "agents", "machine-learning"]},

    {"id": "learn", "name": "学习教育", "icon": "📚", "desc": "教程、课程与学习资源",
     "topics": ["education", "learning", "course", "tutorial"]},

    {"id": "media", "name": "媒体娱乐", "icon": "🎬", "desc": "视频、音乐、直播与游戏",
     "topics": ["video", "music", "media", "streaming", "games"]},

    {"id": "security", "name": "安全隐私", "icon": "🔒", "desc": "安全、隐私与加密工具",
     "topics": ["security", "privacy", "cryptography", "vpn", "password"]},

]


TOKEN = os.environ.get("GITHUB_TOKEN", "")

SLEEP = 1.0 if TOKEN else 2.5


def gh_search(query, per_page=10):
    """一次 Search API 调用，返回 items 列表；遇限流等 60 秒再试一次。"""
    url = f"{API}?q={urllib.request.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-trending-dashboard",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    for attempt in range(2):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8")).get("items", [])
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            print(f"  [warn] {e.code} {query}: {body}", file=sys.stderr)
            if attempt == 0:
                time.sleep(60)
                continue
            return []
        except Exception as e:  # 网络抖动等
            print(f"  [warn] {e} {query}", file=sys.stderr)
            time.sleep(5)
            return []
        finally:
            time.sleep(SLEEP)
    return []


def clean(repo):
    return {
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "html_url": repo.get("html_url"),
        "description": repo.get("description") or "",
        "language": repo.get("language"),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "issues": repo.get("open_issues_count", 0),
        "created_at": (repo.get("created_at") or "")[:10],
        "pushed_at": (repo.get("pushed_at") or "")[:10],
        "topics": (repo.get("topics") or [])[:5],
        "license": (repo.get("license") or {}).get("spdx_id"),
        "avatar": (repo.get("owner") or {}).get("avatar_url"),
    }


def translate_one(text):
    """一条英文简介翻成中文；失败返回 ''（下次运行再试）。"""
    params = urllib.parse.urlencode({
        "client": "dict-chrome-ex", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text,
    })
    url = "https://translate.googleapis.com/translate_a/single?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            zh = "".join(seg[0] for seg in data[0] if seg and seg[0])
            return zh.strip()
        except Exception as e:
            print(f"  [warn] translate failed ({attempt + 1}/3): {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return ""


def pick(cat, seen, now):
    """给一个分类取前 10 个不重复项目。"""
    d60 = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    d180 = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    d30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    pool = {}

    def run(queries):
        for q in queries:
            for item in gh_search(q):
                fn = item.get("full_name")
                if fn and fn not in seen and fn not in pool:
                    pool[fn] = clean(item)
            if len(pool) >= 10:
                break

    if cat["id"] == "all":
        run([f"created:>{d30} stars:>300"])
    else:
        run([f"topic:{t} created:>{d60}" for t in cat["topics"]])
        if len(pool) < 10:
            run([f"topic:{t} created:>{d180}" for t in cat["topics"]])

    top = sorted(pool.values(), key=lambda r: r["stars"], reverse=True)[:10]
    for r in top:
        seen.add(r["full_name"])
    return top


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 翻译缓存：{英文原文: 中文}，随 data/ 一起提交进仓库
    cache_path = os.path.join(data_dir, "translations.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
        except Exception:
            cache = {}

    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")

    seen = set()
    cats = []
    for cat in CATEGORIES:
        print(f"[{cat['id']}] fetching...")
        repos = pick(cat, seen, now)
        print(f"[{cat['id']}] got {len(repos)}")
        cats.append({
            "id": cat["id"], "name": cat["name"], "icon": cat["icon"],
            "desc": cat["desc"], "repos": repos,
        })

    # 翻译缺失的简介（按原文去重，带间隔，失败留空下次再试）
    todo = []
    for c in cats:
        for r in c["repos"]:
            d = r.get("description") or ""
            if d and d not in cache and d not in todo:
                todo.append(d)
    for d in todo:
        zh = translate_one(d)
        if zh:
            cache[d] = zh
        time.sleep(2)
    if todo:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        done = sum(1 for d in todo if d in cache)
        print(f"translated {done} / {len(todo)} new descriptions")
    for c in cats:
        for r in c["repos"]:
            r["description_zh"] = cache.get(r.get("description") or "", "")

    payload = {
        "date": date_str,
        "fetched_at": now.strftime("%Y-%m-%d %H:%M") + " CST",
        "categories": cats,
    }

    day_path = os.path.join(data_dir, f"{date_str}.json")
    with open(day_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(os.path.join(data_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    index_path = os.path.join(data_dir, "index.json")
    dates = []
    if os.path.exists(index_path):
        try:
            dates = json.load(open(index_path, encoding="utf-8")).get("dates", [])
        except Exception:
            dates = []
    if date_str not in dates:
        dates.append(date_str)
    dates.sort()
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False, indent=2)

    total = sum(len(c["repos"]) for c in cats)
    print(f"done: {day_path} ({total} repos, {len(cats)} categories)")


if __name__ == "__main__":
    main()
