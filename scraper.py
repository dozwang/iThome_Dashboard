import requests, time, re, json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import pandas as pd

def fetch_channel_data(name, base_url):
    articles = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    cutoff = datetime(2026, 1, 1)
    max_p = 50 if name == "全站最新" else 10
    
    for page in range(max_p):
        try:
            resp = requests.get(f"{base_url}?page={page}", headers=headers, timeout=25)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.views-row, .item, .node-article')
            if not items: break
            
            found_older = False
            for it in items:
                t_el = it.select_one('.views-field-title a, .title a, h2 a')
                d_el = it.select_one('.views-field-created, .post-at, .date, .created, .time')
                a_el = it.select_one('.views-field-field-author, .author, .field-name-field-author, .views-field-field-reporter, span.author')
                
                if t_el and d_el:
                    try:
                        dt_m = re.search(r'\d{4}-\d{2}-\d{2}', d_el.get_text())
                        post_dt = datetime.strptime(dt_m.group(), '%Y-%m-%d')
                    except: continue
                    
                    if post_dt < cutoff:
                        found_older = True
                        continue
                    
                    raw_a = a_el.get_text(separator=' ', strip=True) if a_el else "iThome 編輯"
                    nm = re.sub(r'^(文|編譯|特約記者|特約)\s*/\s*', '', raw_a)
                    nm = nm.split('|')[0].strip().split(' ')[0]
                    if not nm or len(nm) < 2: nm = "iThome 編輯"
                    
                    iso = post_dt.isocalendar()
                    mon = post_dt - timedelta(days=post_dt.weekday())
                    sun = mon + timedelta(days=6)
                    wk = f"W{iso[1]:02d} ({mon.strftime('%m/%d')}-{sun.strftime('%m/%d')})"
                    
                    articles.append({
                        'url_p': t_el['href'],
                        'ch': name,
                        'author': nm,
                        'week': wk,
                        'title': t_el.get_text(strip=True)
                    })
            if found_older: break
            time.sleep(0.1)
        except: break
    return articles

def create_web_page(data):
    now = datetime.now(timezone(timedelta(hours=8)))
    days = (now.replace(tzinfo=None) - datetime(2026, 1, 1)).days + 1
    df = pd.DataFrame(data)
    if df.empty: return
    
    df_a = df.drop_duplicates(subset=['url_p']).copy()
    a_piv = df_a.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
    a_piv['總計'] = a_piv.sum(axis=1)
    a_piv['日均產量'] = (a_piv['總計'] / days).round(2)
    a_piv = a_piv.sort_values('總計', ascending=False)
    a_piv.index.name = "作者姓名"; a_piv.columns.name = None
    
    c_piv = df.pivot_table(index='ch', columns='week', values='title', aggfunc='count', fill_value=0)
    c_piv['總計'] = c_piv.sum(axis=1)
    c_piv.index.name = "頻道名稱"; c_piv.columns.name = None
    top = c_piv.loc[['全站最新']] if '全站最新' in c_piv.index else pd.DataFrame()
    oth = c_piv.drop(index='全站最新', errors='ignore').sort_values('總計', ascending=False)
    c_piv = pd.concat([top, oth])
    
    c_l, c_v = df.groupby('ch').size().index.tolist(), df.groupby('ch').size().values.tolist()
    
    html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>2026 戰情室</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body{{background:#f8f9fa;padding:25px;font-family:sans-serif;}}
        .card{{border:none;box-shadow:0 4px 15px rgba(0,0,0,0.1);margin-bottom:25px;border-radius:12px;overflow:hidden;}}
        .table thead{{background:#212529;color:#fff;}}
        .table td{{text-align:center;vertical-align:middle;}}
        .table td:first-child{{text-align:left!important;font-weight:bold;background:#fafafa;padding-left:15px;}}
    </style></head>
    <body><div class="container-fluid">
        <h2>📊 iThome 2026 數據統計戰情室</h2>
        <div class="text-muted mb-4">統計天數：{days} 天 | 更新時間：{now.strftime('%Y-%m-%d %H:%M')}</div>
        <div class="row">
            <div class="col-xl-9">
                <div class="card"><div class="card-header fw-bold">👤 作者發文實績</div>
                <div class="table-responsive">{a_piv.to_html(classes='table table-bordered table-sm', border=0)}</div></div>
                <div class="card"><div class="card-header fw-bold">📅 頻道產能統計</div>
                <div class="table-responsive">{c_piv.to_html(classes='table table-bordered table-sm', border=0)}</div></div>
            </div>
            <div class="col-xl-3"><div class="card"><div class="card-body"><canvas id="c"></canvas></div></div></div>
        </div>
    </div>
    <script>new Chart(document.getElementById('c'),{{type:'doughnut',data:{{labels:{json.dumps(c_l,ensure_ascii=False)},datasets:[{{data:{json.dumps(c_v)},backgroundColor:['#0d6efd','#6610f2','#6f42c1','#d63384','#dc3545','#fd7e14','#ffc107','#20c997']}}]}}}});</script>
    </body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    urls = {"全站最新":"https://www.ithome.com.tw/latest","永續IT":"https://www.ithome.com.tw/sustainableit","醫療IT":"https://www.ithome.com.tw/healthit","AI":"https://www.ithome.com.tw/ai","Cloud":"https://www.ithome.com.tw/cloud","人物":"https://www.ithome.com.tw/people","資安":"https://www.ithome.com.tw/security"}
    res = []
    for n, u in urls.items(): res.extend(fetch_channel_data(n, u))
    if res: create_web_page(res)
