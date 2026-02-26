import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import os

def fetch_channel_data(channel_name, base_url):
    articles = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    }
    cutoff_date = datetime(2026, 1, 1)
    
    # 每個頻道嘗試爬取前 3 頁，確保不會漏掉 2026 年初的文章
    for page in range(0, 3):
        url = f"{base_url}?page={page}"
        print(f"正在爬取 {channel_name} (第 {page} 頁): {url}")
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200: break
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # iThome 通用的文章容器標籤
            items = soup.select('.views-row, .item') 
            
            if not items: break

            page_has_2026 = False
            for item in items:
                title_el = item.select_one('.views-field-title a, .title a')
                # 兼容多種日期標籤格式
                date_el = item.select_one('.views-field-created, .post-at, .date, .created')
                
                if title_el and date_el:
                    date_str = date_el.text.strip()
                    try:
                        # 處理 YYYY-MM-DD 或 YYYY/MM/DD
                        clean_date = date_str.replace('/', '-').split(' ')[0]
                        post_date = datetime.strptime(clean_date[:10], '%Y-%m-%d')
                    except:
                        continue

                    if post_date < cutoff_date:
                        continue
                    
                    page_has_2026 = True
                    author_el = item.select_one('.views-field-field-author, .author, .field-name-field-author')
                    
                    articles.append({
                        'channel': channel_name,
                        'title': title_el.text.strip(),
                        'url': "https://www.ithome.com.tw" + title_el['href'] if title_el['href'].startswith('/') else title_el['href'],
                        'author': author_el.text.strip() if author_el else "iThome 編輯",
                        'date': post_date,
                        'week': f"W{post_date.isocalendar().week:02d}"
                    })
            
            # 如果這一頁完全沒有 2026 的文章，就不必爬下一頁
            if not page_has_2026 and page > 0: break
            time.sleep(1.5) # 禮貌間隔
            
        except Exception as e:
            print(f"發生錯誤: {e}")
            break
            
    return articles

def create_web_page(all_articles):
    df = pd.DataFrame(all_articles)
    
    if df.empty:
        print("!!! 警告：最終資料庫為空，請檢查爬蟲 Log !!!")
        html_content = "<html><body style='text-align:center;padding:50px;'><h1>目前尚無 2026 年資料</h1><p>請檢查 GitHub Actions Log 偵錯訊息。</p></body></html>"
    else:
        # 1. 頻道每週發文統計
        channel_weekly = df.pivot_table(index='channel', columns='week', values='title', aggfunc='count', fill_value=0)
        # 2. 作者與頻道貢獻
        author_stats = df.pivot_table(index='author', columns='channel', values='title', aggfunc='count', fill_value=0)
        # 3. 過去一個月清單
        one_month_ago = datetime.now() - pd.Timedelta(days=30)
        list_df = df[df['date'] >= one_month_ago].sort_values('date', ascending=False).copy()
        list_df['title'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
        list_df = list_df[['date', 'channel', 'author', 'title']]
        list_df['date'] = list_df['date'].dt.strftime('%Y-%m-%d')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>iThome 頻道戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                body {{ background-color: #f8f9fa; padding: 40px 15px; font-family: "Microsoft JhengHei", sans-serif; }}
                .card {{ border: none; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.05); margin-bottom: 30px; }}
                .card-title {{ color: #0d6efd; font-weight: bold; border-left: 5px solid #0d6efd; padding-left: 10px; }}
                table {{ background: white; }}
                thead {{ background: #0d6efd; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="text-center mb-5">
                    <h1 class="display-5 fw-bold">🚀 iThome 頻道統計戰情室</h1>
                    <p class="lead text-muted">自動追蹤 2026 年起各頻道與作者動態</p>
                    <span class="badge bg-secondary">最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
                
                <div class="card"><div class="card-body"><h5 class="card-title mb-4">📅 頻道每週發文量 (2026)</h5>
                    <div class="table-responsive">{channel_weekly.to_html(classes='table table-hover table-bordered')}</div>
                </div></div>

                <div class="card"><div class="card-body"><h5 class="card-title mb-4">👤 作者領域貢獻統計</h5>
                    <div class="table-responsive">{author_stats.to_html(classes='table table-hover table-bordered')}</div>
                </div></div>

                <div class="card"><div class="card-body"><h5 class="card-title mb-4">📝 過去 30 天文章清單</h5>
                    <div class="table-responsive">{list_df.to_html(classes='table table-striped', escape=False, index=False)}</div>
                </div></div>
            </div>
        </body>
        </html>
        """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    channels = {
        "永續IT": "https://www.ithome.com.tw/sustainableit",
        "醫療IT": "https://www.ithome.com.tw/healthit",
        "AI": "https://www.ithome.com.tw/ai",
        "Cloud": "https://www.ithome.com.tw/cloud",
        "人物": "https://www.ithome.com.tw/people",
        "資安": "https://www.ithome.com.tw/security"
    }
    
    all_data = []
    for name, url in channels.items():
        results = fetch_channel_data(name, url)
        all_data.extend(results)
        print(f"-> {name} 頻道共抓取 {len(results)} 篇。")
    
    create_web_page(all_data)
    print(f"\n全部完成！總計抓取 {len(all_data)} 篇文章。")
