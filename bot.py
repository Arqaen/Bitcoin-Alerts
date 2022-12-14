# Libraries
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
import json
from tinydb import TinyDB, Query

# Import config file
with open('config.json', 'r') as f:
    try:
        config = json.load(f)
    except:
        print("Error loading config.json")
        exit()

# Get config data
token = config['token']
pw = config['password']
dbname = config['db']
currency = config['currency']
db = TinyDB(dbname)
updater = Updater(token)
dp = updater.dispatcher

# Variables
statusPassword = False
statusAlerts = False
statusRemove = False
statusAbove = False
statusBelow = False

# Listener

def empty(update: Update, context: CallbackContext) -> None:

    print(update.message.text)
    uid = update.message.chat_id

    if statusRemove == True:
        removeit(update, context, update.message.text)

    if statusPassword == True:
        addwhiltelist(update, context, update.message.text)

    if statusAbove == True:
        above(update, context, update.message.text)

    if statusBelow == True:
        below(update, context, update.message.text)

    if statusAlerts == True:
        stats(update, context, update.message.text, uid)

# No input commands

def getId(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"Your id is {update.message.chat_id}")

# Basic commands

def stop(update: Update, context: CallbackContext) -> None:
    global statusRemove, statusPassword, statusAbove, statusBelow
    if statusRemove == True or statusPassword == True or statusAbove == True or statusBelow == True:
        statusRemove = False
        statusPassword = False
        statusAbove = False
        statusBelow = False
        update.message.reply_text("Action stopped")
    else:
        update.message.reply_text("No action to stop")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello, I'm a bot that will alert you when the price of bitcoin is higher or lower than the value you set. To start, type /help")
    statusPassword = False

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("The commands are: \n\n\n/help - To see the list of commands \n\n/start - Start the bot \n\n/price - Get the price of bitcoin\n\n/alert - Create a new alert\n\n/active - Check the active alerts\n\n/remove - Remove some alert\n\n/id - Get the id of the chat\n\n/status - Get the current status and change it\n\n/stop - Stop the current action\n\n/rate - Get the current rate of the USD-EUR\n\n/btcEur - Get the price of bitcoin in EUR\n\n/btcUsd - Get the price of bitcoin in USD\n\n")

# Change status 

def stats(update: Update, context: CallbackContext, response, uid) -> None:
    global statusAlerts

    if statusAlerts == True and response != None:

        response = response.lower()
        tabla = Query()
        temp = db.get(tabla.id == str(uid))

        if response == "y" or response == "yes":
            temp["status"] = "false"
            db.update(temp, tabla.id == str(uid))
            update.message.reply_text("Alerts will be deleted once they are notified")

        elif response == "n" or response == "no":
            temp["status"] = "true"
            db.update(temp, tabla.id == str(uid))
            update.message.reply_text("Alerts will not be deleted once they are notified")

        statusAlerts = False

def status(update: Update, context: CallbackContext) -> None:

    global statusAlerts
    statusAlerts = True
    tabla = Query()
    temp = db.get(tabla.id == str(update.message.chat_id))
    value = temp["status"]

    if value == "true":
        current = "Current status: Not deleting after notified."
    if value == "false":
        current = "Current status: Deleting after notified."

    update.message.reply_text(f"Do you want to delete the alerts once they are notified? Y/n\n{current}")

# Remove alerts

def remove(update: Update, context: CallbackContext) -> None:
    global statusRemove
    statusRemove = True
    update.message.reply_text("Please send me the price of the alert you want to remove")

def removeit(update: Update, context: CallbackContext, response=None) -> None:
    global statusRemove

    if statusRemove == True and response != None:

        status = False
        if response.isdigit():

            try:
                with open(f'{dbname}', 'r') as f:
                    try:
                        data = json.load(f)
                        data = data["_default"]
                    except:
                        pass

                for i in data:
                    i = str(i)
                    if str(data[i]['id']) == str(update.message.chat_id):
                        tabla = Query()
                        temp = db.get(tabla.id == str(update.message.chat_id))
                        for x in data[i]['btc']['above']:
                            if str(data[i]['btc']['above'][x]) == str(response):
                                status = True
                                temp["btc"]["above"].pop(x)
                                
                        for w in data[i]['btc']['below']:
                            if str(data[i]['btc']['below'][w]) == str(response):
                                status = True
                                temp["btc"]["below"].pop(w)

                if status == True:
                    db.update(temp, tabla.id == str(update.message.chat_id))
                    update.message.reply_text("Alert removed")          

                if status == False:
                    update.message.reply_text("Alert not found")

            except:
                update.message.reply_text("Alert not found")

        else:
            update.message.reply_text("Please send me a number")
        
        statusRemove = False
    
# Add to whitelist

def addwhiltelist(update: Update, context: CallbackContext, response=None) -> None:
    global statusPassword
    if checkWhitelist(update.message.chat_id) == True:
        update.message.reply_text("You are already whitelisted")
    else:
        if statusPassword == True and response != None:
            if response == pw:
                update.message.reply_text("Password correct, you are now in the whitelist")
                db.insert({"id":f"{update.message.chat_id}","status":"false","btc":{"above":{},"below":{}}})
            else:
                update.message.reply_text("Password incorrect")
    statusPassword = False

def password(update: Update, context: CallbackContext) -> None:
    global statusPassword
    statusPassword = True
    update.message.reply_text("Please send me the password")

# Create alerts functions

def alert(update: Update, context: CallbackContext) -> None:

    keyboard = [
        [
            InlineKeyboardButton("Above of", callback_data=1),
            InlineKeyboardButton("Below of", callback_data=2),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose the type of alert:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please send me the price you want to set the alert")

    global statusAbove, statusBelow
    if str(query.data) == '1':
        statusAbove = True
    elif str(query.data) == '2':
        statusBelow = True

def above(update: Update, context: CallbackContext, response=None) -> None:
    
    global statusAbove
    if statusAbove == True and response != None:

        if response.isdigit():

            price = getPrice(currency)
            if int(response) < price:
                update.message.reply_text(f"The price is already higher than the value you set (Btc: {price})")

            else:
                tabla = Query()
                key = getKey('above', update.message.chat_id,response) 
                if key == -1:
                    update.message.reply_text("The alert is already in the list")

                if key != None:
                    key = key + 1
                if key == None:
                    update.message.reply_text(f"You are not in the whitelist, please contact an admin")

                if key:

                    temp = db.get(tabla.id == str(update.message.chat_id))
                    temp["btc"]["above"][str(key)] = response
                    db.update(temp, tabla.id == str(update.message.chat_id))

                    update.message.reply_text(f"Ok, I will alert you when the price of bitcoin is higher than {response}")
    
        else:
            update.message.reply_text("Please send me a number")
    statusAbove = False

def below(update: Update, context: CallbackContext, response=None) -> None:
    
    global statusBelow
    if statusBelow == True and response != None:

        if response.isdigit():

            price = getPrice(currency)
            if int(response) > price:
                update.message.reply_text(f"The price is already lower than the value you set (Btc: {price})")

            else:
                tabla = Query()
                key = getKey('below', update.message.chat_id,response) 
                if key == -1:
                    update.message.reply_text("The alert is already in the list")                
                if key == None:
                    update.message.reply_text(f"You are not in the whitelist, please contact an admin")
                if key != None:
                    key = key + 1

                if key:

                    temp = db.get(tabla.id == str(update.message.chat_id))
                    temp["btc"]["below"][str(key)] = response
                    db.update(temp, tabla.id == str(update.message.chat_id))

                    update.message.reply_text(f"Ok, I will alert you when the price of bitcoin is lower than {response}")
    
        else:
            update.message.reply_text("Please send me a number")
    statusBelow = False

def active(update: Update, context: CallbackContext) -> None:

    try:
        indatabase = False  
        empt = True
        with open(f'{dbname}', 'r') as f:
            data = json.load(f)
            data = data["_default"]

            for i in data:
                i = str(i)
                if str(data[i]['id']) == str(update.message.chat_id):
                    indatabase = True
                    text = "Active alerts: \n\nAbove of: \n"

                    if len(data[i]['btc']['above']) > 0 or len(data[i]['btc']['below']) > 0:
                        empt = False

                    if empt == False:

                        for x in data[i]['btc']['above']:
                            text = text + f"{data[i]['btc']['above'][x]} \n"
                                
                        text = text + "\nBelow of: \n"
                        for w in data[i]['btc']['below']:
                            text = text + f"{data[i]['btc']['below'][w]} \n"
                        update.message.reply_text(text)

                    else:
                        update.message.reply_text("You don't have any active alerts")

            if empt == True:
                if indatabase == False:                    
                    update.message.reply_text("You don't have any active alerts")
    except:
        if indatabase == False and empt == True:
            update.message.reply_text("You don't have any active alerts")

# Database functions

def checkWhitelist(id):
    with open(f'{dbname}', 'r') as f:
        try:
            data = json.load(f)
            data = data["_default"]
        except:            
            return False

    for i in data:
        i = str(i)
        if str(data[i]['id']) == str(id):
            return True
    return False

def getKey(type, id, text):

    with open(f'{dbname}', 'r') as f:
        try:
            data = json.load(f)
            data = data["_default"]
        
            for i in data:
                i = str(i)
                if str(data[i]['id']) == str(id):
                    for x in data[i]['btc'][type]:
                        x = str(x)
                        if text == data[i]['btc'][type][x]:
                            return -1
                    
                    key = len(data[i]['btc'][type])
                    try:
                        if data[i]['btc'][type][key]:
                            return key
                    except:
                        return (key+1)

        except:
            return None

# Other functions

def btcEur(update: Update, context: CallbackContext) -> None:
    price = getPrice('EUR')
    update.message.reply_text(f"The price of bitcoin is {price} EUR")

def btcUsd(update: Update, context: CallbackContext) -> None:
    price = getPrice('USDT')
    update.message.reply_text(f"The price of bitcoin is {price} USD")

def btc(update: Update, context: CallbackContext) -> None:
    price = []
    for currency in ['EUR','USDT']:
        price.append(getPrice(currency))
    update.message.reply_text(f"The price of bitcoin is {price[0]} EUR and {price[1]} USD")

def rate(update: Update, context: CallbackContext) -> None:
    rate = getRate()
    if rate:
        update.message.reply_text(f"The rate is: 1 USD = {rate} EUR")

def getPrice(currency):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{currency}"
    try:
        data = requests.get(url)
        data = data.json()
        price = data['price']
        return int(float(price))
    except:
        pass 

def getRate():
    url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: status code {response.status_code}")
        return None

    data = response.json()
    rate
    return round(data["rates"]["EUR"],3)

if __name__ == '__main__':

    # General commands
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('price', btc))
    updater.dispatcher.add_handler(CommandHandler('btcEur', btcEur))
    updater.dispatcher.add_handler(CommandHandler('btcUsd', btcUsd))
    updater.dispatcher.add_handler(CommandHandler('rate', rate))
    updater.dispatcher.add_handler(CommandHandler('active', active))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('id', getId))

    # Input commands
    updater.dispatcher.add_handler(CommandHandler('password', password))
    updater.dispatcher.add_handler(CommandHandler('remove', remove))
    updater.dispatcher.add_handler(CommandHandler('status', status))
    updater.dispatcher.add_handler(CommandHandler('alert', alert))

    # Specific commands
    updater.dispatcher.add_handler(MessageHandler(Filters.text, empty))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    updater.idle()






