from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
import json
import sqlite3

# Load configuration
with open('config.json', 'r') as f:
    try:
        config = json.load(f)
    except Exception as e:
        print("Error loading config.json:", e)
        exit()

token = config['token']
pw = config['password']
dbname = config['db']
currency = config['currency']

# Initialize SQLite (check_same_thread=False for multithreaded context)
db_conn = sqlite3.connect(dbname, check_same_thread=False)
db_cursor = db_conn.cursor()

# Initialize the database tables if they don't exist
def init_db():
    db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id TEXT PRIMARY KEY,
            deletion_status TEXT
        )
    """)
    db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            type TEXT,
            value INTEGER,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        )
    """)
    db_conn.commit()

init_db()

# Global status flags for conversation steps
statusPassword = False
statusAlerts = False
statusRemove = False
statusAbove = False
statusBelow = False

# Database helper functions
def check_whitelist(chat_id):
    db_cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (str(chat_id),))
    return db_cursor.fetchone() is not None

def add_user(chat_id):
    db_cursor.execute("INSERT INTO users (chat_id, deletion_status) VALUES (?, ?)", (str(chat_id), "false"))
    db_conn.commit()

def update_status(chat_id, new_status):
    db_cursor.execute("UPDATE users SET deletion_status = ? WHERE chat_id = ?", (new_status, str(chat_id)))
    db_conn.commit()

def get_user_status(chat_id):
    db_cursor.execute("SELECT deletion_status FROM users WHERE chat_id = ?", (str(chat_id),))
    row = db_cursor.fetchone()
    return row[0] if row else None

def alert_exists(chat_id, alert_type, value):
    db_cursor.execute("SELECT alert_id FROM alerts WHERE chat_id = ? AND type = ? AND value = ?", (str(chat_id), alert_type, int(value)))
    return db_cursor.fetchone() is not None

def add_alert(chat_id, alert_type, value):
    # Always ensure int
    value_int = int(value)
    if alert_exists(chat_id, alert_type, value_int):
        return False
    db_cursor.execute("INSERT INTO alerts (chat_id, type, value) VALUES (?, ?, ?)", (str(chat_id), alert_type, value_int))
    db_conn.commit()
    return True

def get_active_alerts(chat_id):
    db_cursor.execute("SELECT type, value FROM alerts WHERE chat_id = ?", (str(chat_id),))
    return db_cursor.fetchall()

def remove_alert(chat_id, value):
    db_cursor.execute("DELETE FROM alerts WHERE chat_id = ? AND value = ?", (str(chat_id), int(value)))
    db_conn.commit()
    return db_cursor.rowcount

def remove_all_alerts(chat_id):
    """Remove all alerts for a particular user"""
    db_cursor.execute("DELETE FROM alerts WHERE chat_id = ?", (str(chat_id),))
    db_conn.commit()
    return db_cursor.rowcount

# Telegram bot command handlers
def empty(update: Update, context: CallbackContext):
    global statusPassword, statusAlerts, statusRemove, statusAbove, statusBelow
    text = update.message.text
    uid = update.message.chat_id
    print("Received:", text)

    if statusRemove:
        removeit(update, context, text)
    elif statusPassword:
        addwhitelist(update, context, text)
    elif statusAbove:
        above(update, context, text)
    elif statusBelow:
        below(update, context, text)
    elif statusAlerts:
        stats(update, context, text, uid)

def getId(update: Update, context: CallbackContext):
    update.message.reply_text(f"Your id is {update.message.chat_id} 😎")

def stop(update: Update, context: CallbackContext):
    global statusRemove, statusPassword, statusAbove, statusBelow, statusAlerts
    if statusRemove or statusPassword or statusAbove or statusBelow or statusAlerts:
        statusRemove = False
        statusPassword = False
        statusAbove = False
        statusBelow = False
        statusAlerts = False
        update.message.reply_text("Action stopped 👍")
    else:
        update.message.reply_text("No action to stop ⚠️")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello 👋, I'm a bot that alerts you when Bitcoin crosses a set price. Type /help to see commands.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Commands 📚:\n"
        "/help - List commands ℹ️\n"
        "/start - Start the bot 🚀\n"
        "/price - Get the price of Bitcoin 💰\n"
        "/alert - Create a new alert 🚨\n"
        "/active - Show active alerts 📢\n"
        "/remove - Remove an alert ❌\n"
        "/removeAll - Remove ALL your alerts at once ❌\n"
        "/id - Get your chat id 😎\n"
        "/status - Change alert deletion status after notification 🔄\n"
        "/stop - Cancel the current action 🛑\n"
        "/rate - Get the current USD-EUR exchange rate 💱\n"
        "/btcEur - Get Bitcoin price in EUR 💶\n"
        "/btcUsd - Get Bitcoin price in USD 💵"
    )

# Change alert deletion status
def stats(update: Update, context: CallbackContext, response, uid):
    global statusAlerts
    if statusAlerts and response is not None:
        response = response.lower()
        if not check_whitelist(uid):
            update.message.reply_text("You are not whitelisted. Please use /password to register 🔒")
            statusAlerts = False
            return

        if response in ["y", "yes"]:
            # "false" = auto-delete after triggered
            update_status(uid, "false")
            update.message.reply_text("Alerts will be deleted once notified ✅")
        elif response in ["n", "no"]:
            # "true" = do NOT auto-delete
            update_status(uid, "true")
            update.message.reply_text("Alerts will remain after notification 🤖")
        else:
            update.message.reply_text("Invalid response. Please reply with Y or N ❓")
        statusAlerts = False

def status(update: Update, context: CallbackContext):
    global statusAlerts
    statusAlerts = True
    user_status = get_user_status(update.message.chat_id)
    if user_status is None:
        update.message.reply_text("You are not whitelisted. Please use /password to register 🔒")
    else:
        current = "Not deleting after notification 😃" if user_status == "true" else "Deleting after notification 🗑️"
        update.message.reply_text(
            f"Do you want alerts to be deleted after they are notified? (Y/n) 🔔\nCurrent status: {current}"
        )

# Remove a single alert
def remove(update: Update, context: CallbackContext):
    global statusRemove
    statusRemove = True
    update.message.reply_text("Please send the price value of the alert you wish to remove 🔍")

def removeit(update: Update, context: CallbackContext, response=None):
    global statusRemove
    if statusRemove and response is not None:
        if response.isdigit():
            count = remove_alert(update.message.chat_id, response)
            if count > 0:
                update.message.reply_text("Alert removed ✅")
            else:
                update.message.reply_text("Alert not found ❌")
        else:
            update.message.reply_text("Please send a valid number 🔢")
        statusRemove = False

# Remove all alerts command
def removeAll(update: Update, context: CallbackContext):
    if not check_whitelist(update.message.chat_id):
        update.message.reply_text("You are not whitelisted. Please use /password to register 🔒")
        return

    count = remove_all_alerts(update.message.chat_id)
    if count > 0:
        update.message.reply_text(f"All {count} alerts removed 🚮")
    else:
        update.message.reply_text("You have no active alerts to remove 🚫")

# Whitelisting
def addwhitelist(update: Update, context: CallbackContext, response=None):
    global statusPassword
    chat_id = update.message.chat_id
    if statusPassword and response is not None:
        if check_whitelist(chat_id):
            update.message.reply_text("You are already whitelisted 👍")
        else:
            if response == pw:
                add_user(chat_id)
                update.message.reply_text("Password correct ✅. You are now whitelisted!")
            else:
                update.message.reply_text("Password incorrect ❌")
    statusPassword = False

def password(update: Update, context: CallbackContext):
    global statusPassword
    statusPassword = True
    chat_id = update.message.chat_id
    if check_whitelist(chat_id):
        update.message.reply_text("You are already whitelisted 👍")
    else:
        update.message.reply_text("Please send me the password 🔒")

# Creating Alerts
def alert(update: Update, context: CallbackContext):
    if not check_whitelist(update.message.chat_id):
        update.message.reply_text("You are not whitelisted. Please use /password first 🔒")
        return

    keyboard = [
        [InlineKeyboardButton("Above", callback_data="above"),
         InlineKeyboardButton("Below", callback_data="below")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Please choose the type of alert 🚨:", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    query.edit_message_text(text="Please send me the price at which you want to set the alert 💰")

    global statusAbove, statusBelow
    if query.data == 'above':
        statusAbove = True
    elif query.data == 'below':
        statusBelow = True

def above(update: Update, context: CallbackContext, response=None):
    global statusAbove
    if statusAbove and response is not None:
        if response.isdigit():
            # Remove the "check current price" logic so the user can always set the alert
            if alert_exists(update.message.chat_id, "above", response):
                update.message.reply_text("This alert is already in your list ❌")
            else:
                if add_alert(update.message.chat_id, "above", response):
                    update.message.reply_text(f"I will alert you when Bitcoin is above {response} 🔔")
                else:
                    update.message.reply_text("Failed to add alert ❌")
        else:
            update.message.reply_text("Please send a valid number 🔢")
    statusAbove = False

def below(update: Update, context: CallbackContext, response=None):
    global statusBelow
    if statusBelow and response is not None:
        if response.isdigit():
            if alert_exists(update.message.chat_id, "below", response):
                update.message.reply_text("This alert is already in your list ❌")
            else:
                if add_alert(update.message.chat_id, "below", response):
                    update.message.reply_text(f"I will alert you when Bitcoin is below {response} 🔔")
                else:
                    update.message.reply_text("Failed to add alert ❌")
        else:
            update.message.reply_text("Please send a valid number 🔢")
    statusBelow = False

def active(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not check_whitelist(chat_id):
        update.message.reply_text("You are not whitelisted. Please use /password to register 🔒")
        return

    alerts = get_active_alerts(chat_id)
    if not alerts:
        update.message.reply_text("You don't have any active alerts 😕")
        return

    above_alerts = [str(val) for typ, val in alerts if typ == "above"]
    below_alerts = [str(val) for typ, val in alerts if typ == "below"]
    text = (
        "Active alerts 📢:\n\n"
        "Above:\n" + ("\n".join(above_alerts) if above_alerts else "None") +
        "\n\nBelow:\n" + ("\n".join(below_alerts) if below_alerts else "None")
    )
    update.message.reply_text(text)

# Price and Rate Functions
def btcEur(update: Update, context: CallbackContext):
    price = getPrice('EUR')
    if price is None:
        update.message.reply_text("Error fetching price for EUR. Try again later.")
        return
    update.message.reply_text(f"The price of Bitcoin is {price} EUR 💶")

def btcUsd(update: Update, context: CallbackContext):
    price = getPrice('USDT')
    if price is None:
        update.message.reply_text("Error fetching price for USD. Try again later.")
        return
    update.message.reply_text(f"The price of Bitcoin is {price} USD 💵")

def btc(update: Update, context: CallbackContext):
    price_eur = getPrice('EUR')
    price_usd = getPrice('USDT')
    if price_eur is None or price_usd is None:
        update.message.reply_text("Error fetching prices. Try again later.")
        return
    update.message.reply_text(f"Bitcoin is {price_eur} EUR 💶 and {price_usd} USD 💵")

def rate(update: Update, context: CallbackContext):
    exchange_rate = getRate()
    if exchange_rate:
        update.message.reply_text(f"💱 1 USD = {exchange_rate} EUR")
    else:
        update.message.reply_text("Error fetching USD-EUR exchange rate.")

def getPrice(curr):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{curr}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return int(float(data['price']))

def getRate():
    url = "https://open.er-api.com/v6/latest/USD"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return round(data["rates"]["EUR"], 3)

# Main: Register handlers and start polling
if __name__ == '__main__':
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(CommandHandler('stop', stop))
    dp.add_handler(CommandHandler('id', getId))
    dp.add_handler(CommandHandler('price', btc))
    dp.add_handler(CommandHandler('btcEur', btcEur))
    dp.add_handler(CommandHandler('btcUsd', btcUsd))
    dp.add_handler(CommandHandler('rate', rate))
    dp.add_handler(CommandHandler('active', active))
    dp.add_handler(CommandHandler('password', password))
    dp.add_handler(CommandHandler('remove', remove))
    dp.add_handler(CommandHandler('removeAll', removeAll))  # <-- New command
    dp.add_handler(CommandHandler('status', status))
    dp.add_handler(CommandHandler('alert', alert))
    dp.add_handler(MessageHandler(Filters.text, empty))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()
