import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import pytz
import os
import json
from concurrent.futures import ThreadPoolExecutor

--- 配置 ---
SITE_TITLE = "iThome 2026 數據戰情室"
DATA_FILE = "ithome_data.csv"
TW_TZ = pytz.timezone('Asia/Taipei')
TARGET_YEAR = 2026

def get_now():
return datetime.datetime.now(TW_TZ)

def parse_page(url, channel_name):
articles = []
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
try:
resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, 'html.parser')
items = soup.select(".view-content .item")

def main():
with open('feeds.json', 'r', encoding='utf-8') as f:
config = json.load(f)

def render_html(weekly, channels, author_content):
week_rows = "".join([f"<div class='item'><span>第 {k} 週</span><b>{v} 篇</b></div>" for k, v in weekly.items()])
ch_rows = "".join([f"<div class='item'><span>{k}</span><b>{v} 篇</b></div>" for k, v in channels.items()])

if name == "main":
main()
