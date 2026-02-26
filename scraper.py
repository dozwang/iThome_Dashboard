import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import pandas as pd
import time
import re
import json

def fetch_channel_data(channel_name, base_url):
    articles = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    cutoff_date = datetime(2026, 1, 1)
    # 針對全站最新增加深度，確保涵蓋 2026 至今所有文章
    max_pages = 25 if channel_name == "全站最新" else 6
    
    for page in range(0, max_pages):
        url = f"{base_url}?page={page}"
        print(f"正在爬取 {channel_name} (第 {page} 頁): {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.views-row, .item') 
            if not items: break

            found_older = False
            for item in items:
                title_el = item.select_one('.views-field-title a, .title a')
                date_el = item.select_one('.views-field-created, .post-at, .date, .created')
                author_el = item.select_one('.views-field-field-author, .field-name-field-author, .views-field-field-reporter, .author')
                
                if title_el and date_el:
                    try:
                        clean_date_str = re.search(r'\d{4}-\d{2}-\d{2}', date_el.text).group()
                        post_date = datetime.strptime(clean_date_str, '%Y-%m-%d')
                    except: continue

                    if post_date < cutoff_date:
                        found_older = True
                        continue
                    
                    raw_author = author_el.get_text(strip=True) if author_el else "iThome 編輯"
                    author_name = re.sub(r'^(文|編譯|特約記者)\s*/\s*', '', raw_author)
                    author_name = re.split(r'[||\d{4}]', author_name)[0].strip()
                    if not author_name: author_name = "iThome 編輯"

                    monday = post_date - timedelta(days=post_date.weekday())
                    sunday = monday + timedelta(days=6)
                    iso_year, iso_week, iso_day = post_date.isocalendar()
                    week_label = f"W{iso_week:02d} ({monday.strftime('%m/%d')}-{sunday.strftime('%m/%d')})"

                    articles.append({
                        'url_path': title_el['href'],
                        'channel': channel_name,
                        'title': title_el.text.strip(),
                        'url': "https://www.ithome.com.tw" + title_el['href'] if title_el['href'].startswith('/') else title_el['href'],
                        'author': author_name,
                        'date': post_date,
                        'week_label': week_label
                    })
            if found_older: break
            time.sleep(0.5)
        except Exception as e:
            print(f"錯誤: {e}")
            break
    return articles

def create_web_page(all_articles):
    now_tw = datetime.now(timezone(timedelta(hours=8)))
    tw_time_str = now_tw.strftime('%Y-%m-%d %H:%M')
    # 計算 2026/1/1 至今總天數用於計算日均值
    days_since_start = (now_tw.replace(tzinfo=None) - datetime(2026, 1, 1)).days + 1
    
    df_raw = pd.DataFrame(all_articles)
    if df_raw.empty:
        with open("index.html", "w", encoding="utf-8") as f: f.write("<h1>無資料</h1>")
        return

    # 1. 作者矩陣 (不重複計)
    df_author = df_raw.drop_duplicates(subset=['url_path']).copy()
    author_pivot = df_author.pivot_table(index='author', columns='week_label', values='title', aggfunc='count', fill_value=0)
    author_pivot['總計'] = author_pivot.sum(axis=1)
    author_pivot['日均發文'] = (author_pivot['總計'] / days_since_start).round(2)
    author_pivot = author_pivot.sort_values('總計', ascending=False)
    author_pivot.index.name = None
    author_pivot.columns.name = None

    # 2. 頻道矩陣 (含重複)
    channel_pivot = df_raw.pivot_table(index='channel', columns='week_label', values='title', aggfunc='count', fill_value=0)
    channel_pivot['總計'] = channel_pivot.sum(axis=1)
    channel_pivot['日均產量'] = (channel_pivot['總計'] / days_since_start).round(2)
    channel_pivot.index.name = None
    channel_pivot.columns.name = None

    # 頻道排序：全站最新置頂，其餘按總計排序
    other_ch = channel_pivot.drop(index='全站最新', errors='ignore').sort_values('總計', ascending=False)
    if '全站最新' in channel_pivot.index:
        channel_pivot = pd.concat([channel_pivot.loc[['全站最新']], other_ch])

    # 圖表
    channel_total = df_raw.groupby('channel').size().sort_values(ascending=False)
    chart_labels = channel_total.index.tolist()
    chart_values = channel_total.values.tolist()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>iThome 2026 戰情室</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; font-family: "Microsoft JhengHei", sans-serif; }}
            .card {{ border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; border-radius: 12px; }}
            .card-header {{ background: #fff; font-weight: bold; color: #0d6efd; }}
            .table thead {{ background: #212529; color: white; text-align: center; }}
            .table td {{ text-align: center; vertical-align: middle; }}
            .table td:first-child {{ text-align: left; padding-left: 15px; font-weight: bold; min-width: 120px; }}
            .avg-col {{ background-color: #fffdec; font-weight: bold; color: #dc3545; }}
            .total-col {{ background-color: #f1f3f5; font-weight: bold; }}
            h2 {{ color: #0d6efd; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h2>📊 iThome 2026 數據戰情室</h2>
                <span class="badge bg-dark">最後更新：{tw_time_str} (台北)</span>
            </div>
            <div class="row">
                <div class="col-xl-9">
                    <div class="card">
                        <div class="card-header">👤 作者發文實績 (含日均產能)</div>
                        <div class="card-body p-0"><div class="table-responsive">
                            {author_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                        </div></div>
                    </div>
                    <div class="card">
                        <div class="card-header">📅 頻道經營統計 (全站置頂)</div>
                        <div class="card-body p-0"><div class="table-responsive">
                            {channel_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                        </div></div>
                    </div>
                </div>
                <div class="col-xl-3">
                    <div class="card"><div class="card-body">
                        <h5 class="fw-bold mb-3">📈 頻道佔比</h5>
                        <canvas id="channelChart"></canvas>
                    </div></div>
                </div>
            </div>
        </div>
        <script>
            new Chart(document.getElementById('channelChart'), {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(chart_labels, ensure_ascii=False)},
                    datasets: [{{
                        data: {json.dumps(chart_values)},
                        backgroundColor: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#20c997']
                    }}]
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)

if __name__ == "__main__":
    channels = {
        "全站最新": "https://www.ithome.com.tw/latest",
        "永續IT": "https://www.ithome.com.tw/sustainableit",
        "醫療IT": "https://www.ithome.com.tw/healthit",
        "AI": "https://www.ithome.com.tw/ai",
        "Cloud": "https://www.ithome.com.tw/cloud",
        "人物": "https://www.ithome.com.tw/people",
        "資安": "https://www.ithome.com.tw/security"
    }
    all_data = []
    for name, url in channels.items(): all_data.extend(fetch_channel_data(name, url))
    create_web_page(all_data)
    print("✅ 報表更新完成，已加入日均發文量。")
