import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import re

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
                        # 處理格式如 "2026-02-25發表" 或 "2026-02-25"
                        clean_date_str = re.search(r'\d{4}-\d{2}-\d{2}', date_raw).group()
                        post_date = datetime.strptime(clean_date_str, '%Y-%m-%d')
                    except:
                        continue

                    if post_date < cutoff_date:
                        continue
                    
                    page_has_2026 = True
                    
                    # --- 作者人名清洗邏輯 ---
                    raw_author = author_el.get_text(strip=True) if author_el else "iThome 編輯"
                    # 使用 Regex 去除 "文/"、"文 /"、"編譯/" 以及後方可能連帶的日期
                    # 邏輯：取 "文/" 之後的文字，並過濾掉任何日期字串
                    author_name = re.sub(r'^(文|編譯|特約記者)\s*/\s*', '', raw_author)
                    author_name = author_name.split('|')[0].split('202')[0].strip() # 剔除日期雜質
                    
                    if not author_name: author_name = "iThome 編輯"

                    articles.append({
                        'channel': channel_name,
                        'title': title_el.text.strip(),
                        'url': "https://www.ithome.com.tw" + title_el['href'] if title_el['href'].startswith('/') else title_el['href'],
                        'author': author_name,
                        'date': post_date,
                        'week': f"W{post_date.isocalendar().week:02d}"
                    })
            
            if not page_has_2026 and page > 0: break
            time.sleep(1)
            
        except Exception as e:
            print(f"爬取錯誤: {e}")
            break
            
    return articles

def create_web_page(all_articles):
    df = pd.DataFrame(all_articles)
    
    if df.empty:
        html_content = "<html><body style='padding:50px;text-align:center;'><h1>目前尚無 2026 年資料</h1></body></html>"
    else:
        # 統計每位作者每週發文量
        author_weekly = df.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
        # 統計頻道產量
        channel_stats = df.pivot_table(index='channel', columns='week', values='title', aggfunc='count', fill_value=0)
        
        # 文章明細
        list_df = df.sort_values('date', ascending=False).copy()
        list_df['title'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
        list_df = list_df[['date', 'author', 'channel', 'title']]
        list_df['date'] = list_df['date'].dt.strftime('%Y-%m-%d')

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>iThome 2026 戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                body {{ background-color: #f0f2f5; padding: 30px; }}
                .card {{ border: none; box-shadow: 0 4px 8px rgba(0,0,0,0.08); margin-bottom: 25px; }}
                .table thead {{ background: #343a40; color: white; }}
                h2 {{ color: #1a73e8; font-weight: bold; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📊 iThome 作者發文戰情室 (2026)</h2>
                <p class="text-muted">自動更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="card"><div class="card-body">
                    <h5 class="fw-bold mb-3">👤 作者每週發文統計 (已清洗人名)</h5>
                    <div class="table-responsive">{author_weekly.to_html(classes='table table-hover table-bordered')}</div>
                </div></div>

                <div class="card"><div class="card-body">
                    <h5 class="fw-bold mb-3">📝 近期文章明細</h5>
                    <div class="table-responsive">{list_df.to_html(classes='table table-striped', escape=False, index=False)}</div>
                </div></div>
            </div>
        </body>
        </html>
        """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    channels = {{
        "永續IT": "https://www.ithome.com.tw/sustainableit",
        "醫療IT": "https://www.ithome.com.tw/healthit",
        "AI": "https://www.ithome.com.tw/ai",
        "Cloud": "https://www.ithome.com.tw/cloud",
        "人物": "https://www.ithome.com.tw/people",
        "資安": "https://www.ithome.com.tw/security"
    }}
    
    all_data = []
    for name, url in channels.items():
        all_data.extend(fetch_channel_data(name, url))
    
    create_web_page(all_data)
    print(f"成功處理 {len(all_data)} 篇文章。")
