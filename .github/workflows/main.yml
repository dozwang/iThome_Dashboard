name: iThomeUpdate

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: SetupPython
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: Install
        run: pip install requests beautifulsoup4 pandas

      - name: Run
        run: python scraper.py

      - name: Push
        run: |
          git config --local user.name "github-actions[bot]"
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git add index.html
          git commit -m "Auto Update" || echo "No changes"
          git push origin main
