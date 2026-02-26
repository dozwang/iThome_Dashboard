import requests, time, re, json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import pandas as pd

def get_real_author(article_url):
    """進入文章內頁抓取真實作者姓名"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # 停頓一下避免被封鎖
        time.sleep(0.1)
        resp = requests.get(article_url, headers=headers, timeout=15)
        if resp.status_code != 200: return "iThome 編輯"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 內頁常見的作者選擇器
        author_el = soup.select_one('.reporter, .author, .field-name-field-author, .views-field-field-reporter')
        
        if author_el:
            raw_text = author_el.get_text(strip=True)
            # 清洗格式：文/周峻佑 -> 周峻佑
            name = re.sub(r'^(文|編譯|特約記者|特約|記者)\s*/\s*', '', raw_text)
            name = name.split('|')[0].strip().split(' ')[0].split('（')[0]
            return name if len(name) >= 2 else "iThome 編輯"
    except:
        pass
    return "iThome 編輯"

def fetch_channel_data(name, base_url):
    articles = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    cutoff = datetime(2026, 1, 1)
    # 由於要進內頁，我們先將頁數微調（全站 30 頁，其餘 5 頁）以免執行過久
    max_p = 30 if name == "全站最新" else 5
    
    for page in range(max_p):
        try:
            resp = requests.get(f"{base_url}?page={page}", headers=headers, timeout=20)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.views-row, .item, .node-article')
            if not items: break
            
            found_older = False
            for it in items:
                t_el = it.select_one('.views-field-title a, .title a, h2 a')
                d_el = it.select_one('.views-field-created, .post-at, .date, .created, .time')
                
                if t_el and d_el:
                    try:
                        dt_m = re.search(r'\d{4}-\d{2}-\d{2}', d_el.get_text())
                        post_dt = datetime.strptime(dt_m.group(), '%Y-%m-%d')
                    except: continue
                    
                    if post_dt < cutoff:
                        found_older = True
                        continue
                    
                    # 取得文章連結並進入抓取真實作者
                    path = t_el['href']
                    full_url = "https://www.ithome.com.tw" + path if path.startswith('/') else path
                    print(f"  [內頁抓取] {t_el.get_text(strip=True)[:20]}...")
                    real_author = get_real_author(full_url)
                    
                    iso = post_dt.isocalendar()
                    mon = post_dt - timedelta(days=post_dt.weekday())
                    sun = mon + timedelta(days=6)
                    wk = f"W{iso[1]:02d} ({mon.strftime('%m/%d')}-{sun.strftime('%m/%d')})"
                    
                    articles.append({
                        'url_p': path,
                        'ch': name,
                        'author': real_author,
                        'week': wk,
                        'title': t_el.get_text(strip=True)
                    })
            if found_older: break
        except: break
    return articles

def create_web_page(data):
    now = datetime.now(timezone(timedelta(hours=8)))
    days = (now.replace(tzinfo=None) - datetime(2026, 1, 1)).days + 1
    df = pd.DataFrame(data)
    if df.empty: return
    
    # 作者表
    df_a = df.drop_duplicates(subset=['url_p']).copy()
    a_piv = df_a.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
    a_piv['總計'] = a_piv.sum(axis=1)
    a_piv['日均'] = (a_piv['總計'] / days).round(2)
    a_piv = a_piv.sort_values('總計', ascending=False)
    a_piv.index.name = "作者姓名"; a_piv.columns.name = None
    
    # 頻道表
    c_piv = df.pivot_table(index='ch', columns='week', values='title', aggfunc='count', fill_value=0)
    c_piv['總計'] = c_piv.sum(axis=1)
    c_piv.index.name = "頻道名稱"; c_piv.columns.name = None
    top = c_piv.loc[['全站最新']] if '全站最新' in c_piv.index else pd.DataFrame()
    oth = c_piv.drop(index='全站最新', errors='ignore').sort_values('總計', ascending=False)
    c_piv = pd.concat([top, oth])
    
    cl, cv = df.groupby('ch').size().index.tolist(), df.groupby('ch').size().values.tolist()
    
    html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>2026 戰情室</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>body{{background:#f8f9fa;padding:25px;font-family:sans-serif;}}.card{{border:none;box-shadow:0 4px 15px rgba(0,0,0,0.1);margin-bottom:25px;border-radius:12px;}}.table thead{{background:#212529;color:#fff;}}.table td{{text-align:center;}}.table td:first-child{{text-align:left!important;font-weight:bold;background:#fafafa;padding-left:15px;}}</style></head>
    <body><div class="container-fluid"><h2>📊 iThome 2026 數據統計戰情室</h2><p class="text-muted">最後更新：{now.strftime('%Y-%m-%d %H:%M')}</p>
    <div class="row"><div class="col-xl-9"><div class="card"><div class="card-header fw-bold">👤 記者發文實績 (內頁真實姓名)</div><div class="table-responsive">{a_piv.to_html(classes='table table-bordered table-sm', border=0)}</div></div>
    <div class="card"><div class="card-header fw-bold">📅 頻道產能統計</div><div class="table-responsive">{c_piv.to_html(classes='table table-bordered table-sm', border=0)}</div></div></div>
    <div class="col-xl-3"><div class="card"><div class="card-body"><canvas id="c"></canvas></div></div></div></div></div>
    <script>new Chart(document.getElementById('c'),{{type:'doughnut',data:{{labels:{json.dumps(cl,ensure_ascii=False)},datasets:[{{data:{json.dumps(cv)},backgroundColor:['#0d6efd','#6610f2','#6f42c1','#d63384','#dc3545','#fd7e14','#ffc107','#20c997']}}]}}}});</script></body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    urls = {"全站最新":"https://www.ithome.com.tw/latest","永續IT":"https://www.ithome.com.tw/sustainableit","醫療IT":"https://www.ithome.com.tw/healthit","AI":"https://www.ithome.com.tw/ai","Cloud":"https://www.ithome.com.tw/cloud","人物":"https://www.ithome.com.tw/people","資安":"https://www.ithome.com.tw/security"}
    res = []
    for n, u in urls.items():
        print(f">>> 開始處理頻道: {n}")
        res.extend(fetch_channel_data(n, u))
    if res: create_web_page(res)
