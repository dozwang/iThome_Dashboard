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
    
    for page in range(0, 3):
        url = f"{base_url}?page={page}"
        print(f"正在爬取 {channel_name} (第 {page} 頁): {url}")
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200: break
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.views-row, .item') 
            if not items: break

            page_has_2026 = False
            for item in items:
                title_el = item.select_one('.views-field-title a, .title a')
                date_el = item.select_one('.views-field-created, .post-at, .date, .created')
                author_el = item.select_one('.views-field-field-author, .field-name-field-author, .views-field-field-reporter, .author')
                
                if title_el and date_el:
                    date_raw = date_el.text.strip()
                    try:
                        clean_date_str = re.search(r'\d{4}-\d{2}-\d{2}', date_raw).group()
                        post_date = datetime.strptime(clean_date_str, '%Y-%m-%d')
                    except:
                        continue

                    if post_date < cutoff_date: continue
                    page_has_2026 = True
                    
                    # 作者人名清洗：只留下人名
                    raw_author = author_el.get_text(strip=True) if author_el else "iThome 編輯"
                    author_name = re.sub(r'^(文|編譯|特約記者)\s*/\s*', '', raw_author)
                    author_name = re.split(r'[||\d{4}]', author_name)[0].strip()
                    if not author_name: author_name = "iThome 編輯"

                    # 計算週標籤：WXX (MM/DD-MM/DD)
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
            if not page_has_2026 and page > 0: break
            time.sleep(1)
        except Exception as e:
            print(f"爬取錯誤: {e}")
            break
    return articles

def create_web_page(all_articles):
    tw_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    df_raw = pd.DataFrame(all_articles)
    
    if df_raw.empty:
        html_content = f"<html><body><h1 style='text-align:center;'>目前無 2026 年資料</h1></body></html>"
    else:
        # 排序週標籤
        df_raw = df_raw.sort_values(['week_label', 'date'])
        
        # 1. 作者發文實績 (週發文矩陣)
        # 先去重，確保同一篇文章不重複計入作者產量
        df_author = df_raw.drop_duplicates(subset=['url_path']).copy()
        author_pivot = df_author.pivot_table(index='author', columns='week_label', values='title', aggfunc='count', fill_value=0)
        
        # 增加右側「總計」欄位
        author_pivot['總計'] = author_pivot.sum(axis=1)
        author_pivot = author_pivot.sort_values('總計', ascending=False)
        
        # 2. 頻道統計 (含全站最新，允許重複計入分流)
        channel_pivot = df_raw.pivot_table(index='channel', columns='week_label', values='title', aggfunc='count', fill_value=0)
        channel_pivot['總計'] = channel_pivot.sum(axis=1)
        
        # 圖表數據
        channel_total = df_raw.groupby('channel').size().sort_values(ascending=False)
        chart_labels = channel_total.index.tolist()
        chart_values = channel_total.values.tolist()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>iThome 2026 戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ background-color: #f8f9fa; padding: 25px; font-family: "Microsoft JhengHei", sans-serif; }}
                .card {{ border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; border-radius: 15px; }}
                .card-header {{ background-color: #fff; border-bottom: 1px solid #eee; font-weight: bold; color: #0d6efd; }}
                .table thead {{ background: #212529; color: white; }}
                .table-sm td, .table-sm th {{ font-size: 0.9rem; text-align: center; vertical-align: middle; }}
                .author-name {{ text-align: left !important; font-weight: bold; background: #fdfdfd; }}
                .total-col {{ background-color: #e9ecef; font-weight: bold; }}
                h2 {{ color: #0d6efd; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2>📊 iThome 作者發文戰情室</h2>
                    <span class="badge bg-dark">最後更新：{tw_time} (台北)</span>
                </div>

                <div class="row">
                    <div class="col-lg-9">
                        <div class="card">
                            <div class="card-header">👤 每位作者每週發文實績 (不重複計)</div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    {author_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">📅 頻道每週發文統計 (含全站最新 & 分流重複計)</div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    {channel_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-3">
                        <div class="card">
                            <div class="card-header">📈 頻道分佈佔比</div>
                            <div class="card-body">
                                <canvas id="channelChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                const ctx = document.getElementById('channelChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'doughnut',
                    data: {{
                        labels: {json.dumps(chart_labels, ensure_ascii=False)},
                        datasets: [{{
                            data: {json.dumps(chart_values)},
                            backgroundColor: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#20c997']
                        }}]
                    }},
                    options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
                }});
            </script>
        </body>
        </html>
        """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

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
    for name, url in channels.items():
        all_data.extend(fetch_channel_data(name, url))
    create_web_page(all_data)
    print("✅ 儀表板已更新，包含每週作者發文矩陣。")
