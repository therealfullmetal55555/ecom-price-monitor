# Telegram Alert Demo

## Simulated alert that would be sent when competitor price drops

```
📊 Price Monitor Report - 8 comparisons

🚨 Critical: 2 competitors cheaper
• _powerbank_ | My: Powerbank 20000mAh Fast Charge `2490₽` vs Comp: [173592402] `2290₽` (-8.0%)
  PowerCo Powerbank 20000mAh SuperCharge
  https://www.wildberries.ru/catalog/173592402/detail.aspx

• _charger_ | My: Fast Charger 65W GaN `1290₽` vs Comp: [168300345] `1190₽` (-7.8%)
  ChargeMax Fast Charger 65W GaN Ultra
  https://www.wildberries.ru/catalog/168300345/detail.aspx

Threshold: competitor cheaper by > 5% triggers alert
```

## How to trigger real alert in test

```bash
python scripts/test_alert.py
# Or lower threshold:
python -m src.main --threshold 0.01
```

## Screenshot placeholder

Add screenshot from your Telegram after first real run:
`demo/telegram-screenshot.png`

The mock alerter prints to console when TELEGRAM_BOT_TOKEN is not set, so you can demo without real bot.
