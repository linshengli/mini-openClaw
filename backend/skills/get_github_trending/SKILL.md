---
name: get_github_trending
description: 获取 GitHub Trending 最新榜单（daily 或 weekly），可选按 language 过滤并返回 Top N 仓库。当用户提到“GitHub Trending / 今日热门 / 本周热门 / daily trending / weekly trending”时使用。
---

# get_github_trending

1. 解析用户需求，默认参数：`since=daily`、`language=`(空表示全部)、`limit=10`。  
   可接受值：`since` 仅 `daily` 或 `weekly`。

2. 优先使用 `python_repl` 直接抓取并解析 Trending 页面（结构化最稳定）：

```python
import json
import re
import requests
from bs4 import BeautifulSoup

since = "daily"      # daily | weekly
language = ""        # 例如 "python"，空字符串表示全部
limit = 10

url = f"https://github.com/trending/{language}?since={since}" if language else f"https://github.com/trending?since={since}"
html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
soup = BeautifulSoup(html, "html.parser")

items = []
for row in soup.select("article.Box-row")[:limit]:
    a = row.select_one("h2 a")
    if not a:
        continue
    repo = "/".join(a.get_text(" ", strip=True).split())
    href = "https://github.com" + a.get("href", "").strip()
    desc_el = row.select_one("p")
    lang_el = row.select_one('[itemprop="programmingLanguage"]')
    stars_el = row.select_one('a[href$="/stargazers"]')
    period_el = row.select_one("span.d-inline-block.float-sm-right")

    items.append({
        "repo": repo,
        "url": href,
        "description": desc_el.get_text(" ", strip=True) if desc_el else "",
        "language": lang_el.get_text(" ", strip=True) if lang_el else "",
        "stars": stars_el.get_text(" ", strip=True).replace(",", "") if stars_el else "",
        "stars_in_period": re.sub(r"\\s+", " ", period_el.get_text(" ", strip=True)) if period_el else "",
    })

print(json.dumps({"since": since, "language": language or "all", "count": len(items), "items": items}, ensure_ascii=False, indent=2))
```

3. 若 `python_repl` 缺少依赖或抓取失败，再使用 `fetch_url` 获取 `https://github.com/trending?since=<daily|weekly>` 文本并做降级提取，至少返回仓库名列表。

4. 输出时必须包含：`榜单周期`、`抓取URL`、`抓取时间`、`Top列表`（每项含 repo、url、stars、stars_in_period，尽量补充 description/language）。  
   若用户未指定数量，返回 Top 10；若指定则按用户数量返回。
