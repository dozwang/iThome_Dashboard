import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import os

def fetch_data():
    articles = []
    cutoff_date = datetime(2026, 1, 1) # 統計今年開始
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)
    
    # 爬取前 5 頁（可依需求調整）
    for page in range(0, 5):
        url = f"https://www.ithome.com.tw/latest?page={page}"
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        items = soup.select('.views-row')
        
        for item in items:
            date_str = item.select_one('.views-field-created').text.strip()
            post_date = datetime.strptime(date_str, '%Y-%m-%d')
            if post_date < cutoff_date: return articles
            
            articles.append({
                'title': item.select_one('.views-field-title a').text,
                'url': "https://www.ithome.com.tw" + item.select_one('.views-field-title a')['href'],
                'author': item.select_one('.views-field-field-author').text.strip(),
                'channel': item.select_one('.views-field-field-article-category').text.strip(),
                'date': post_date,
                'week': f"W{post_date.isocalendar().week}"
            })
    return articles

def create_web_page(articles):
    df = pd.DataFrame(articles)
    
    # 1. 作者每週發文統計
    weekly_pivot = df.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
    
    # 2. 作者頻道分布
    channel_pivot = df.pivot_table(index='author', columns='channel', values='title', aggfunc='count', fill_value=0)
    
    # 3. 過去一個月清單 (HTML 連結)
    one_month_df = df[df['date'] >= (datetime.now() - timedelta(days=30))].copy()
    one_month_df['title'] = one_month_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
    list_df = one_month_df[['date', 'author', 'channel', 'title']].sort_values('date', ascending=False)

    # 組合 HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>iThome 報表戰情室</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>body {{ padding: 20px; background: #f8f9fa; }} .card {{ margin-bottom: 20px; }}</style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">📊 iThome 作者發文戰情室 (2026)</h1>
            <p class="text-muted">最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="card"><div class="card-body"><h5>📅 每週發文統計</h5>{weekly_pivot.to_html(classes='table table-striped table-hover')}</div></div>
            <div class="card"><div class="card-body"><h5>🏷️ 頻道分佈</h5>{channel_pivot.to_html(classes='table table-striped table-hover')}</div></div>
            <div class="card"><div class="card-body"><h5>📝 過去一個月文章清單</h5>{list_df.to_html(classes='table table-sm', escape=False, index=False)}</div></div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    data = fetch_data()
    create_web_page(data)
