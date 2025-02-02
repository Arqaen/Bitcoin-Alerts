from telegram import Bot
import requests
import time
import json
import sqlite3

# Load configuration
try:
    with open('config.json') as f:
        config = json.load(f)
except Exception as e:
    print("Error loading config.json:", e)
    exit()

currency = config['currency']
token = config['token']
sleep_time = config['sleep']
dbname = config['db']

bot = Bot(token)
db_conn = sqlite3.connect(dbname, check_same_thread=False)
db_cursor = db_conn.cursor()

# Helper functions for SQLite access
def get_all_users():
    db_cursor.execute("SELECT chat_id, deletion_status FROM users")
    return db_cursor.fetchall()

def get_user_alerts(chat_id):
    db_cursor.execute("SELECT alert_id, type, value FROM alerts WHERE chat_id = ?", (str(chat_id),))
    return db_cursor.fetchall()

def delete_alert(alert_id):
    db_cursor.execute("DELETE FROM alerts WHERE alert_id = ?", (alert_id,))
    db_conn.commit()

def getPrice():
    """Get the price of BTC in your configured currency (e.g., USDT or EUR)."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{currency}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return int(float(data['price']))

while True:
    price = getPrice()
    if price is None:
        print("Error fetching price. Retrying...")
        time.sleep(sleep_time)
        continue

    print(f"\nBitcoin price: {price} ({currency})\n")

    users = get_all_users()

    # Check each user's alerts
    for user in users:
        chat_id, deletion_status = user

        alerts = get_user_alerts(chat_id)
        triggered_alert_ids = []

        for alert_id, alert_type, alert_value in alerts:
            # Compare as integers
            if alert_type == "above" and price > alert_value:
                bot.send_message(chat_id=int(chat_id),
                                 text=f"🚀 Bitcoin price is above {alert_value} {currency}! Current price: {price}")
                triggered_alert_ids.append(alert_id)

            elif alert_type == "below" and price < alert_value:
                bot.send_message(chat_id=int(chat_id),
                                 text=f"🚀 Bitcoin price is below {alert_value} {currency}! Current price: {price}")
                triggered_alert_ids.append(alert_id)

        # If user status = "false", remove triggered alerts
        # "false" means: delete alert after sending
        if deletion_status == "false" and triggered_alert_ids:
            for a_id in triggered_alert_ids:
                delete_alert(a_id)

        # Small delay to avoid flooding if many users
        time.sleep(1)

    # Sleep before next price check
    time.sleep(sleep_time)
