import feedparser, datetime, pytz, os, requests, json, re, sys
from dateutil import parser as date_parser
from collections import Counter

# --- 基本設定 ---
SITE_TITLE = "iThome 作者與頻道戰情室"
TW_TZ = pytz.timezone('Asia/Taipei')

def load_config():
    if os.path.exists('feeds.json'):
        with open('feeds.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {"FEEDS": {"TW": []}}

def fetch_data():
    config = load_config()
    all_articles = []
    # 統計用容器
    author_counts = Counter()
    channel_counts = Counter()
    weekly_counts = Counter()
    author_articles = {} # 記錄作者過去一個月的文章

    now = datetime.datetime.now(TW_TZ)
    one_month_ago = now - datetime.timedelta(days=30)
    this_year_start = datetime.datetime(now.year, 1, 1, tzinfo=TW_TZ)

    for item in config['FEEDS']['TW']:
        try:
            resp = requests.get(item['url'], timeout=10, verify=False)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                # 取得時間
                try: p_date = date_parser.parse(entry.get('published')).astimezone(TW_TZ)
                except: p_date = now
                
                # 過濾：只看今年開始的文章
                if p_date < this_year_start: continue

                author = entry.get('author', '未知作者')
                channel = item['tag']
                week_str = f"W{p_date.strftime('%U')}" # 第幾週
                
                # 統計邏輯
                author_counts[author] += 1
                channel_counts[channel] += 1
                weekly_counts[week_str] += 1

                # 記錄過去一個月的文章清單
                if p_date >= one_month_ago:
                    if author not in author_articles: author_articles[author] = []
                    author_articles[author].append({
                        'title': entry.title,
                        'link': entry.link,
                        'date': p_date.strftime('%m/%d')
                    })
        except: continue
    
    return {
        "author_counts": dict(author_counts.most_common(10)),
        "channel_counts": dict(channel_counts),
        "weekly_counts": dict(sorted(weekly_counts.items())),
        "author_articles": author_articles
    }

def generate_html(data):
    # 這裡將資料渲染進 HTML (省略重複的 CSS，參考你原本的戰情室風格)
    # 使用 Chart.js 可以更專業地呈現 Data Science 的感覺
    stats_html = "".join([f"<div class='stat-row'><span>{k}</span><b>{v}</b></div>" for k, v in data['author_counts'].items()])
    
    author_detail_html = ""
    for auth, posts in data['author_articles'].items():
        links = "".join([f"<li><a href='{p['link']}'>[{p['date']}] {p['title']}</a></li>" for p in posts])
        author_detail_html += f"<h3>{auth} (近30天)</h3><ul>{links}</ul>"

    full_html = f"""
    <html><head><meta charset='UTF-8'><title>{SITE_TITLE}</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f4f7f6; }}
        .dashboard {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
        .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .stat-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 5px 0; }}
        h2 {{ border-left: 5px solid #3498db; padding-left: 10px; }}
    </style></head><body>
        <h1>{SITE_TITLE}</h1>
        <div class="dashboard">
            <div class="card"><h2>作者發文排行 (2026)</h2>{stats_html}</div>
            <div class="card"><h2>頻道分佈</h2>{ "".join([f"<div class='stat-row'><span>{k}</span><b>{v}</b></div>" for k, v in data['channel_counts'].items()]) }</div>
            <div class="card"><h2>每週發文趨勢</h2>{ "".join([f"<div class='stat-row'><span>{k}</span><b>{v}</b></div>" for k, v in data['weekly_counts'].items()]) }</div>
        </div>
        <hr>
        <h2>作者文章清單 (過去一個月)</h2>
        <div class="card">{author_detail_html}</div>
    </body></html>
    """
    with open('index.html', 'w', encoding='utf-8') as f: f.write(full_html)

if __name__ == "__main__":
    data = fetch_data()
    generate_html(data)
