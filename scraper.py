import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import os

def fetch_data():
    articles = []
    # 模擬瀏覽器，避免被 iThome 阻擋
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    cutoff_date = datetime(2026, 1, 1)
    
    for page in range(0, 5):
        url = f"https://www.ithome.com.tw/latest?page={page}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 修正後的選擇器
            items = soup.select('.views-row')
            
            if not items:
                break

            for item in items:
                title_el = item.select_one('.views-field-title a')
                date_el = item.select_one('.views-field-created')
                author_el = item.select_one('.views-field-field-author')
                cat_el = item.select_one('.views-field-field-article-category')

                if title_el and date_el:
                    post_date = datetime.strptime(date_str := date_el.text.strip(), '%Y-%m-%d')
                    if post_date < cutoff_date:
                        return articles
                    
                    articles.append({
                        'title': title_el.text.strip(),
                        'url': "https://www.ithome.com.tw" + title_el['href'],
                        'author': author_el.text.strip() if author_el else "未知作者",
                        'channel': cat_el.text.strip() if cat_el else "未分類",
                        'date': post_date,
                        'week': f"W{post_date.isocalendar().week:02d}"
                    })
        except Exception as e:
            print(f"爬取第 {page} 頁時發生錯誤: {e}")
            
    return articles

def create_web_page(articles):
    # 如果沒資料，建立一個帶有欄位的空 DataFrame 避免 KeyError
    cols = ['title', 'url', 'author', 'channel', 'date', 'week']
    df = pd.DataFrame(articles, columns=cols)

    if df.empty:
        html_content = "<html><body><h1>目前尚無資料</h1><p>請確認爬蟲是否成功抓取 iThome 網頁。</p></body></html>"
    else:
        # 進行統計
        weekly_pivot = df.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
        channel_pivot = df.pivot_table(index='author', columns='channel', values='title', aggfunc='count', fill_value=0)
        
        # 過去一個月清單
        one_month_ago = datetime.now() - timedelta(days=30)
        list_df = df[df['date'] >= one_month_ago].copy()
        list_df['title'] = list_df.apply(lambda x: f'<a href="{x["url"]}" target="_blank">{x["title"]}</a>', axis=1)
        list_df = list_df[['date', 'author', 'channel', 'title']].sort_values('date', ascending=False)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>iThome 報表戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>body {{ padding: 20px; }} .card {{ margin-bottom: 20px; }} table {{ font-size: 0.9rem; }}</style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">📊 iThome 作者發文戰情室 (2026)</h1>
                <p>最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <div class="card"><div class="card-body"><h5>📅 每週發文統計</h5>{weekly_pivot.to_html(classes='table table-bordered table-striped')}</div></div>
                <div class="card"><div class="card-body"><h5>🏷️ 頻道分布</h5>{channel_pivot.to_html(classes='table table-bordered table-striped')}</div></div>
                <div class="card"><div class="card-body"><h5>📝 過去一個月文章清單</h5>{list_df.to_html(classes='table table-hover', escape=False, index=False)}</div></div>
            </div>
        </body>
        </html>
        """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    data = fetch_data()
    print(f"成功抓取 {len(data)} 篇文章")
    create_web_page(data)
