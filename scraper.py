import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd

def get_ithome_articles():
    articles = []
    page = 0
    cutoff_date = datetime(2026, 1, 1) # 統計今年開始
    
    while True:
        url = f"https://www.ithome.com.tw/latest?page={page}"
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('.views-row')
        
        if not items: break
        
        for item in items:
            date_str = item.select_one('.views-field-created').text.strip()
            post_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            if post_date < cutoff_date:
                return articles # 停止爬取舊資料
            
            articles.append({
                'title': item.select_one('.views-field-title a').text,
                'url': "https://www.ithome.com.tw" + item.select_one('.views-field-title a')['href'],
                'author': item.select_one('.views-field-field-author').text.strip(),
                'channel': item.select_one('.views-field-field-article-category').text.strip(),
                'date': post_date
            })
        page += 1
    return articles

# 執行統計並產出 Markdown 報表
def generate_report(articles):
    df = pd.DataFrame(articles)
    df['week'] = df['date'].dt.isocalendar().week
    
    # 1. 作者每週發文數量
    weekly_stats = df.groupby(['author', 'week']).size().unstack(fill_value=0)
    
    # 2. 作者頻道分布
    channel_stats = df.groupby(['author', 'channel']).size().unstack(fill_value=0)
    
    # 3. 過去一個月清單 (30天內)
    one_month_ago = datetime.now() - timedelta(days=30)
    recent_df = df[df['date'] >= one_month_ago]
    
    # 寫入 README.md 的邏輯 (略)
    print("Report Generated.")

if __name__ == "__main__":
    data = get_ithome_articles()
    generate_report(data)
