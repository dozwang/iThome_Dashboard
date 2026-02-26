def create_web_page(all_articles):
    tw_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    df_raw = pd.DataFrame(all_articles)
    
    if df_raw.empty:
        html_content = f"<html><body><h1 style='text-align:center;'>目前無 2026 年資料</h1></body></html>"
    else:
        # 1. 作者發文實績
        df_author = df_raw.drop_duplicates(subset=['url_path']).copy()
        author_pivot = df_author.pivot_table(index='author', columns='week_label', values='title', aggfunc='count', fill_value=0)
        author_pivot['總計'] = author_pivot.sum(axis=1)
        author_pivot = author_pivot.sort_values('總計', ascending=False)
        
        # --- 移除表格左上角的贅字 (week_label / author) ---
        author_pivot.index.name = None
        author_pivot.columns.name = None
        
        # 2. 頻道經營統計
        channel_pivot = df_raw.pivot_table(index='channel', columns='week_label', values='title', aggfunc='count', fill_value=0)
        channel_pivot['總計'] = channel_pivot.sum(axis=1)
        channel_pivot.index.name = None
        channel_pivot.columns.name = None
        
        # 頻道排序邏輯 (全站最新置頂)
        other_channels = channel_pivot.drop(index='全站最新', errors='ignore').sort_values('總計', ascending=False)
        if '全站最新' in channel_pivot.index:
            channel_pivot = pd.concat([channel_pivot.loc[['全站最新']], other_channels])
        else:
            channel_pivot = other_channels

        # 圖表數據
        channel_total = df_raw.groupby('channel').size().sort_values(ascending=False)
        chart_labels = channel_total.index.tolist()
        chart_values = channel_total.values.tolist()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>iThome 2026 戰情室</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ background-color: #f8f9fa; padding: 25px; font-family: "Microsoft JhengHei", sans-serif; }}
                .card {{ border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px; border-radius: 12px; }}
                .card-header {{ background-color: #fff; font-weight: bold; color: #0d6efd; border-bottom: 1px solid #eee; }}
                .table thead {{ background: #212529; color: white; text-align: center; }}
                .table td {{ text-align: center; vertical-align: middle; }}
                .total-col {{ background-color: #f1f3f5; font-weight: bold; color: #0d6efd; }}
                h2 {{ color: #0d6efd; font-weight: bold; }}
                /* 強制讓第一列 (作者名) 左對齊 */
                .table td:first-child {{ text-align: left; padding-left: 15px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2>📊 iThome 數據統計戰情室</h2>
                    <span class="badge bg-dark">最後更新：{{tw_time}} (台北)</span>
                </div>

                <div class="row">
                    <div class="col-xl-9">
                        <div class="card">
                            <div class="card-header">👤 每位作者：各週發文數量清單 (不重複計)</div>
                            <div class="card-body p-0">
                                <div class="table-responsive">
                                    {author_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">📅 頻道產量：全站置頂與分流統計 (含重複計)</div>
                            <div class="card-body p-0">
                                <div class="table-responsive">
                                    {channel_pivot.to_html(classes='table table-bordered table-hover table-sm', border=0)}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-xl-3">
                        <div class="card">
                            <div class="card-header">📈 頻道佔比</div>
                            <div class="card-body">
                                <canvas id="channelChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                new Chart(document.getElementById('channelChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: {json.dumps(chart_labels, ensure_ascii=False)},
                        datasets: [{{
                            data: {json.dumps(chart_values)},
                            backgroundColor: ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#20c997']
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
