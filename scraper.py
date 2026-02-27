import requests, time, re, json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import pandas as pd

def get_real_author(article_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        time.sleep(0.05)
        resp = requests.get(article_url, headers=headers, timeout=10)
        if resp.status_code != 200: return "iThome 編輯"
        soup = BeautifulSoup(resp.text, 'html.parser')
        author_el = soup.select_one('.reporter, .author, .field-name-field-author, .views-field-field-reporter')
        if author_el:
            name = re.sub(r'^(文|編譯|特約記者|特約|記者)\s*/\s*', '', author_el.get_text(strip=True))
            return name.split('|')[0].strip().split(' ')[0].split('（')[0]
    except: pass
    return "iThome 編輯"

def fetch_channel_data(name, base_url):
    articles = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    cutoff = datetime(2026, 1, 1)
    # 全站抓取深度增加，子頻道確保抓完前 10 頁
    max_p = 60 if name == "全站最新" else 10
    
    for page in range(max_p):
        try:
            resp = requests.get(f"{base_url}?page={page}", headers=headers, timeout=15)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.views-row, .item, .node-article')
            if not items: break
            
            for it in items:
                t_el = it.select_one('.views-field-title a, .title a, h2 a')
                d_el = it.select_one('.views-field-created, .post-at, .date, .created, .time')
                if t_el and d_el:
                    try:
                        dt_m = re.search(r'\d{4}-\d{2}-\d{2}', d_el.get_text())
                        post_dt = datetime.strptime(dt_m.group(), '%Y-%m-%d')
                    except: continue
                    
                    # 核心修正：檢查該則時間，不屬於 2026 區間的直接跳過，但不停止爬取
                    if post_dt < cutoff:
                        continue
                    
                    path = t_el['href']
                    full_url = "https://www.ithome.com.tw" + path if path.startswith('/') else path
                    real_author = get_real_author(full_url)
                    iso = post_dt.isocalendar()
                    mon = post_dt - timedelta(days=post_dt.weekday())
                    sun = mon + timedelta(days=6)
                    wk = f"W{iso[1]:02d} ({mon.strftime('%m/%d')}-{sun.strftime('%m/%d')})"
                    articles.append({'url_p':path,'ch':name,'author':real_author,'week':wk,'title':t_el.get_text(strip=True)})
            
            # 全站最新頻道若已經出現大量舊文，可提早結束以節省時間
            # 子頻道則建議跑完 max_p 以免遺漏被置頂文夾雜的新文
            time.sleep(0.1)
        except: break
    return articles

def create_web_page(data):
    now = datetime.now(timezone(timedelta(hours=8)))
    days = (now.replace(tzinfo=None) - datetime(2026, 1, 1)).days + 1
    df = pd.DataFrame(data)
    if df.empty: return

    # 1. 頻道經營統計 (置頂)
    c_piv = df.pivot_table(index='ch', columns='week', values='title', aggfunc='count', fill_value=0)
    c_piv['總計'] = c_piv.sum(axis=1)
    c_piv.index.name = "頻道"; c_piv.columns.name = None
    top_c = c_piv.loc[['全站最新']] if '全站最新' in c_piv.index else pd.DataFrame()
    oth_c = c_piv.drop(index='全站最新', errors='ignore').sort_values('總計', ascending=False)
    c_piv = pd.concat([top_c, oth_c])

    # 2. 記者發文實績 (直式排版)
    df_a = df.drop_duplicates(subset=['url_p']).copy()
    a_piv_raw = df_a.pivot_table(index='author', columns='week', values='title', aggfunc='count', fill_value=0)
    a_piv = a_piv_raw.transpose().sort_index(ascending=False)
    a_piv.index.name = "週數"; a_piv.columns.name = None

    cl, cv = df.groupby('ch').size().index.tolist(), df.groupby('ch').size().values.tolist()

    def stylize_table(html_str):
        pattern = r'<td>([6-9]|[1-9][0-9]+)</td>'
        replacement = r'<td class="high-productivity">\1</td>'
        return re.sub(pattern, replacement, html_str)

    html_channel_table = stylize_table(c_piv.to_html(classes='table table-bordered table-sm table-hover', border=0))
    html_author_table = stylize_table(a_piv.to_html(classes='table table-bordered table-sm table-hover', border=0))

    html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body{{background:#f0f2f5;padding:10px;font-family:sans-serif;font-size:12px;line-height:1.2;}}
        .card{{border:none;box-shadow:0 1px 4px rgba(0,0,0,0.05);margin-bottom:10px;border-radius:4px;}}
        .card-header{{background:#fff;font-weight:bold;padding:4px 10px;border-bottom:1px solid #eee;color:#0560bd;font-size:12px;}}
        .table thead th{{background:#2c3e50!important;color:#ffffff!important;border-color:#34495e;position:sticky;top:0;z-index:2;}}
        .table-sm th, .table-sm td{{padding:1px 4px!important;text-align:center;border-color:#dee2e6;vertical-align:middle;}}
        .table-responsive{{max-height:80vh;overflow:auto;}}
        .table td:first-child, .table th:first-child {{
            position:sticky;left:0;z-index:1;background:#f8f9fa!important;text-align:left!important;
            font-weight:bold;min-width:110px;box-shadow:1px 0 3px rgba(0,0,0,0.05);
        }}
        .table thead th:first-child{{z-index:3;color:#ffffff!important;}}
        .high-productivity {{background-color:#c3e6cb!important;color:#155724!important;font-weight:bold!important;}}
        h5{{font-weight:bold;color:#0d6efd;margin-bottom:8px;font-size:16px;}}
    </style></head>
    <body><div class="container-fluid">
        <h5>📊 iThome 2026 數據戰情室</h5>
        <div class="row g-2">
            <div class="col-xl-9">
                <div class="card"><div class="card-header">📅 頻道經營統計 (置頂)</div>
                <div class="table-responsive">{html_channel_table}</div></div>
                <div class="card"><div class="card-header">👤 記者發文實績 (直式排版)</div>
                <div class="table-responsive">{html_author_table}</div></div>
            </div>
            <div class="col-xl-3">
                <div class="card"><div class="card-body p-2"><canvas id="c"></canvas></div></div>
                <div class="text-muted" style="font-size:10px;">最後更新：{now.strftime('%m/%d %H:%M')}</div>
            </div>
        </div>
    </div>
    <script>new Chart(document.getElementById('c'),{{type:'doughnut',data:{{labels:{json.dumps(cl,ensure_ascii=False)},datasets:[{{data:{json.dumps(cv)},backgroundColor:['#0d6efd','#6610f2','#6f42c1','#d63384','#dc3545','#fd7e14','#ffc107','#20c997']}}]}},options:{{plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,font:{{size:10}}}}}}}}}})}});</script>
    </body></html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    urls = {"全站最新":"https://www.ithome.com.tw/latest","永續IT":"https://www.ithome.com.tw/sustainableit","醫療IT":"https://www.ithome.com.tw/healthit","AI":"https://www.ithome.com.tw/ai","Cloud":"https://www.ithome.com.tw/cloud","人物":"https://www.ithome.com.tw/people","資安":"https://www.ithome.com.tw/security"}
    res = []
    for n, u in urls.items(): res.extend(fetch_channel_data(n, u))
    if res: create_web_page(res)
