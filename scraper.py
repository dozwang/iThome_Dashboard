import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
                    
                    # 作者人名清洗
                    raw_author = author_el.get_text(strip=True) if author_el else "iThome 編輯"
                    author_name = re.sub(r'^(文|編譯|特約記者)\s*/\s*', '', raw_author)
                    author_name = author_name.split('|')[0].split('202')[0].strip()
                    if not author_name: author_name = "iThome 編輯"

                    # 計算週標籤
                    monday = post_date - timedelta(days=post_date.weekday())
                    sunday = monday + timedelta(days=6)
                    week_label = f"W{post_date.isocalendar().week:02d} ({monday.strftime('%m/%d')}-{sunday.strftime('%m/%d')})"

                    articles.append({
                        'url_path': title_el['href'], # 用於識別同一篇文章
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
    df_raw = pd.DataFrame(all_articles)
    
    if df_raw.empty:
        html_content = "<html><body style='padding:50px;text-align:center;'><h1>目前尚無 2026 年資料</h1></body></html>"
    else:
        # 排序
        df_raw = df_raw.sort_values('week_label')
        
        # 軌道 1：作者統計（去重，每篇文章只算一次）
        df_author = df_raw.drop_duplicates(subset=['url_path']).copy()
        author_weekly = df_author.pivot_table(index='author', columns='week_label', values='title', aggfunc='count', fill_value=0)
        
        # 軌道 2：頻道統計（不去重，反映分流熱度）
        channel_weekly = df_raw.pivot_table(index='channel', columns='week_label', values='title', aggfunc='count', fill_value=0)
        
        # 圓餅圖數據（使用頻道統計）
        channel_total = df_raw.groupby('channel').size().sort_values(ascending=False)
        chart_labels = channel_total.index.tolist()
        chart_values = channel_total.values.tolist()
        
        # 文章明細（顯示去重後的真實文章清單）
        list_df = df_author.sort_values('date', ascending=False).copy()
        list_df['title'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
        list_df = list_df[['date', 'author', 'title']]
        list_df['date'] = list_df['date'].dt.strftime('%Y-%m-%d')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>iThome 2026 戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ background-color: #f8f9fa; padding: 30px; font-family: "Microsoft JhengHei", sans-serif; }}
                .card {{ border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px; border-radius: 12px; }}
                .table thead {{ background: #212529; color: white; text-align: center; }}
                .table td {{ text-align: center; vertical-align: middle; }}
                h2 {{ color: #0d6efd; font-weight: bold; }}
                .stat-desc {{ font-size: 0.9rem; color: #666; margin-bottom: 1rem; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="d-flex justify-content-between align-items-center mb-4 px-3">
                    <h2>📊 iThome 數據統計戰情室 (2026)</h2>
                    <span class="badge bg-secondary">最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
                </div>
                
                <div class="row">
                    <div class="col-xl-9">
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold">👤 作者發文實績 (不重複計算)</h5>
                            <p class="stat-desc">※ 同一篇文章若分流至多個頻道，在此表中僅計入 1 筆產量。</p>
                            <div class="table-responsive">{author_weekly.to_html(classes='table table-hover table-bordered table-sm')}</div>
                        </div></div>
                        
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold">📅 頻道經營產量 (含重複分流)</h5>
                            <p class="stat-desc">※ 反映各頻道的曝光熱度，分流文章會重複計入各頻道數量。</p>
                            <div class="table-responsive">{channel_weekly.to_html(classes='table table-hover table-bordered table-sm')}</div>
                        </div></div>
                    </div>
                    
                    <div class="col-xl-3">
                        <div class="card"><div class="card-body">
                            <h5 class="fw-bold mb-4">📈 頻道流量佔比</h5>
                            <canvas id="channelChart"></canvas>
                        </div></div>
                    </div>
                </div>

                <div class="card"><div class="card-body">
                    <h5 class="fw-bold mb-4">📝 真實發文清單 (不含分流重複項)</h5>
                    <div class="table-responsive">{list_df.head(60).to_html(classes='table table-striped table-hover', escape=False, index=False)}</div>
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
                            hoverOffset: 10
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
    print(f"完成！總計抓取原始紀錄為 {len(all_data)} 筆。")
