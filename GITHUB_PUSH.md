# Push to GitHub - Quick Start

## Option 1: Create new repo on GitHub UI (recommended)

1. Go to https://github.com/new
2. Repository name: `ecom-competitor-price-monitor`
3. Description: `Competitor price monitor for Wildberries marketplace - portfolio project with rate limiting, SQLite history, Telegram alerts`
4. Visibility: Public
5. **Do NOT** initialize with README, .gitignore, license (we already have them)
6. Click Create

7. Then push:

```bash
# Download and unzip the provided zip
unzip ecom-competitor-price-monitor.zip
cd project-3-price-monitor

# Link to your new repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ecom-competitor-price-monitor.git
git push -u origin main
```

## Option 2: Using gh CLI (if you have it)

```bash
gh repo create ecom-competitor-price-monitor --public --source=. --remote=origin --push
```

## After push - add to portfolio

- Add topics: `wildberries`, `price-monitoring`, `e-commerce`, `telegram-bot`, `apscheduler`, `python`
- Pin repo on GitHub profile
- Add screenshot of Telegram alert to README (replace placeholder)
- Add link to this repo in your main portfolio README

## Local test after clone

```bash
git clone https://github.com/YOUR_USERNAME/ecom-competitor-price-monitor.git
cd ecom-competitor-price-monitor
pip install -r requirements.txt
python scripts/seed_history.py
python scripts/test_alert.py
python run.py
```

Expected: 403 antibot in cloud is OK - handled gracefully. Run locally for real WB data.
