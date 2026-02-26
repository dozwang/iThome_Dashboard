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
    # 設定統計起點
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
                        # 精準擷取 YYYY-MM-DD
                        clean_date_str = re.search(r'\d{4}-\d{2}-\d{2}', date_raw).group()
                        post_date = datetime.strptime(clean_date_str, '%Y-%m-%d')
                    except:
                        continue

                    if post_date < cutoff_date: continue
                    page_has_2026 = True
                    
                    # 作者人名清洗：處理「文/周峻佑」、「文 / 蘇文彬」等格式
                    raw_author = author_el.get_text(strip=True) if author_el else "iThome 編輯"
                    author_name = re.sub(r'^(文|編譯|特約記者)\s*/\s*', '', raw_author)
                    # 再次移除可能存在的日期尾碼
                    author_name = re.split(r'[||\d{4}]', author_name)[0].strip()
                    
                    if not author_name: author_name = "iThome 編輯"

                    # 計算週標籤：W08 (02/16-02/22)
                    monday = post_date - timedelta(days=post_date.weekday())
                    sunday = monday + timedelta(days=6)
                    # 使用 isocalendar 確保週數正確
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
    # 建立台灣時區時間 (UTC+8)
    tw_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    
    df_raw = pd.DataFrame(all_articles)
    
    if df_raw.empty:
        html_content = f"<html><body style='padding:50px;text-align:center;'><h1>目前尚無 2026 年資料</h1><p>更新時間：{tw_time}</p></body></html>"
    else:
        # 確保排序正確 (依週別標籤)
        df_raw = df_raw.sort_values(['week_label', 'date'])
        
        # 1. 作者統計 (去重)
        df_author = df_raw.drop_duplicates(subset=['url_path']).copy()
        author_weekly = df_author.pivot_table(index='author', columns='week_label', values='title', aggfunc='count', fill_value=0)
        
        # 2. 頻道統計 (含重複)
        channel_weekly = df_raw.pivot_table(index='channel', columns='week_label', values='title', aggfunc='count', fill_value=0)
        
        # 圖表數據
        channel_total = df_raw.groupby('channel').size().sort_values(ascending=False)
        chart_labels = channel_total.index.tolist()
        chart_values = channel_total.values.tolist()
        
        # 明細
        list_df = df_author.sort_values('date', ascending=False).copy()
        list_df['title_link'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
        list_df = list_df[['date', 'author', 'title_link']]
        list_df['date'] = list_df['date'].dt.strftime('%Y-%m-%d')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>iThome 2026 戰情室 - {tw_time}</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ background-color: #f8f9fa; padding: 25px; font-family: "Microsoft JhengHei", sans-serif; }}
                .card {{ border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 25px; border-radius: 12px; }}
                h2 {{ color: #0d6efd; font-weight: bold; }}
                .table thead {{ background: #212529; color: white; text-align: center; font-size: 0.9rem; }}
                .table td {{ text-align: center; vertical-align: middle; }}
                .author-cell {{ font-weight: bold; color: #495057; text-align: left !important; }}
                .stat-info {{ font-size: 0.85rem; color: #6c757d; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="d-flex justify-content-between align-items-end mb-4 px-2">
                    <div>
                        <h2>📊 iThome 數據統計戰情室</h2>
                        <div class="stat-info">自動追蹤 2026 年起之發文產能</div>
                    </div>
                    <span class="badge bg-dark mb-2">最後更新 (台北)：{tw_time}</span>
                </div>
                
                <div class="row">
                    <div class="col-xl-9">
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold mb-3">👤 作者發文實績 <small class="text-muted fw-normal">(排除分流，真實產量)</small></h5>
                            <div class="table-responsive">{author_weekly.to_html(classes='table table-hover table-bordered table-sm', border=0)}</div>
                        </div></div>
                        
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold mb-3">📅 頻道經營產量 <small class="text-muted fw-normal">(含跨頻道重複計算)</small></h5>
                            <div class="table-responsive">{channel_weekly.to_html(classes='table table-hover table-bordered table-sm', border=0)}</div>
                        </div></div>
                    </div>
                    
                    <div class="col-xl-3">
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold mb-4">📈 頻道分佈佔比</h5>
                            <canvas id="channelChart"></canvas>
                        </div></div>
                    </div>
                </div>

                <div class="card"><div class="card-body">
                    <h5 class="fw-bold mb-3">📝 2026 文章明細 <small class="text-muted fw-normal">(顯示最新 60 筆)</small></h5>
                    <div class="table-responsive">{list_df.head(60).to_html(classes='table table-striped table-hover', escape=False, index=False, border=0)}</div>
                </div></div>
            </div>

            <script>
                new Chart(document.getElementById('channelChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: {json.dumps(chart_labels, ensure_ascii=False)},
                        datasets: [{{
                            data: {json.dumps(chart_values)},
                            backgroundColor: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#20c997'],
                            borderWidth: 2
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
    print(f"✅ 報表生成完成！總計紀錄: {len(all_data)}")
