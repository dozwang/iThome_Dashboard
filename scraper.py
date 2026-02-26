import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time

def fetch_channel_data(channel_name, url):
    articles = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    cutoff_date = datetime(2026, 1, 1)
    
    print(f"正在爬取 {channel_name}: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"無法存取 {channel_name}, Status: {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 頻道頁面的文章通常位於 .item 或 .views-row
        items = soup.select('.views-row')
        
        for item in items:
            title_el = item.select_one('.views-field-title a')
            date_el = item.select_one('.views-field-created')
            author_el = item.select_one('.views-field-field-author')
            
            if title_el and date_el:
                date_str = date_el.text.strip()
                post_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                if post_date < cutoff_date:
                    continue
                
                articles.append({
                    'channel': channel_name,
                    'title': title_el.text.strip(),
                    'url': "https://www.ithome.com.tw" + title_el['href'],
                    'author': author_el.text.strip() if author_el else "iThome 編輯",
                    'date': post_date,
                    'week': f"W{post_date.isocalendar().week:02d}"
                })
    except Exception as e:
        print(f"爬取 {channel_name} 發生錯誤: {e}")
        
    return articles

def create_web_page(all_articles):
    df = pd.DataFrame(all_articles)
    if df.empty:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write("<html><body><h1>目前尚無 2026 年資料</h1></body></html>")
        return

    # 1. 各頻道每週文章數量統計
    channel_weekly = df.pivot_table(index='channel', columns='week', values='title', aggfunc='count', fill_value=0)
    
    # 2. 每個作者的文章統計 (包含頻道分布)
    author_stats = df.pivot_table(index='author', columns='channel', values='title', aggfunc='count', fill_value=0)
    
    # 3. 過去一個月文章詳細清單
    list_df = df.sort_values('date', ascending=False).copy()
    list_df['title'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
    list_df = list_df[['date', 'channel', 'author', 'title']]

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>iThome 頻道戰情室</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>body {{ padding: 30px; background-color: #f4f7f6; }} .card {{ margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}</style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">🚀 iThome 多頻道發文戰情室</h1>
            <p class="text-muted">更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="card"><div class="card-body"><h5 class="card-title">📅 頻道每週發文量</h5>{channel_weekly.to_html(classes='table table-hover table-bordered')}</div></div>
            <div class="card"><div class="card-body"><h5 class="card-title">👤 作者與頻道貢獻</h5>{author_stats.to_html(classes='table table-hover table-bordered')}</div></div>
            <div class="card"><div class="card-body"><h5 class="card-title">📝 最新文章清單 (2026)</h5>{list_df.to_html(classes='table table-sm', escape=False, index=False)}</div></div>
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
        all_data.extend(fetch_channel_data(name, url))
        time.sleep(1) # 避免請求過於頻繁
    
    create_web_page(all_data)
    print(f"完成！共抓取 {len(all_data)} 篇文章。")
