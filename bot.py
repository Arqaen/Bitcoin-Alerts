from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
import json
from tinydb import TinyDB, Query

with open('config.json', 'r') as f:
    try:
        config = json.load(f)
    except:
        print("Error loading config.json")
        exit()

token = config['token']
pw = config['password']
dbname = config['db']
db = TinyDB(dbname)
updater = Updater(token)
dp = updater.dispatcher

statusRemove = False
statusPassword = False
statusAbove = False
statusBelow = False

def getId(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"Your id is {update.message.chat_id}")

def empty(update: Update, context: CallbackContext) -> None:
    print(update.message.text)
    if statusRemove == True:
        removeit(update, context, update.message.text)

    if statusPassword == True:
        addwhiltelist(update, context, update.message.text)

    if statusAbove == True:
        above(update, context, update.message.text)

    if statusBelow == True:
        below(update, context, update.message.text)
    
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
    
def btc(update: Update, context: CallbackContext) -> None:
    price = getPrice()
    update.message.reply_text(f"The price of bitcoin is {price}")
    
def addwhiltelist(update: Update, context: CallbackContext, response=None) -> None:
    global statusPassword
    if checkWhitelist(update.message.chat_id) == True:
        update.message.reply_text("You are already whitelisted")
    else:
        if statusPassword == True and response != None:
            if response == pw:
                update.message.reply_text("Password correct, you are now in the whitelist")
                db.insert({"id":f"{update.message.chat_id}","btc":{"above":{},"below":{}}})
            else:
                update.message.reply_text("Password incorrect")
    statusPassword = False

def password(update: Update, context: CallbackContext) -> None:
    global statusPassword
    statusPassword = True
    update.message.reply_text("Please send me the password")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello, I'm a bot that will alert you when the price of bitcoin is higher or lower than the value you set. To start, type /help")
    statusPassword = False

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("The commands are: \n\n\n/help - To see the list of commands \n\n/start - Start the bot \n\n/price - Get the price of bitcoin\n\n/alert - Create a new alert\n\n/active - Check the active alerts\n\n/remove - Remove some alert\n\n/id - Get the id of the chat")

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

            price = getPrice()
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

            price = getPrice()
            if int(response) > price:
                update.message.reply_text(f"The price is already lower than the value you set (Btc: {price})")

            else:
                tabla = Query()
                key = getKey('below', update.message.chat_id,response) 
                if key == -1:
                    update.message.reply_text("The alert is already in the list")
                if key != None:
                    key = key + 1
                if key == None:
                    update.message.reply_text(f"You are not in the whitelist, please contact an admin")

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
                    return len(data[i]['btc'][type])

        except:
            return None

def getPrice():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        data = requests.get(url)
        data = data.json()
        price = data['price']
        return int(float(price))
    except:
        pass 

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

def main() -> None:

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('price', btc))
    updater.dispatcher.add_handler(CommandHandler('active', active))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('id', getId))

    updater.dispatcher.add_handler(CommandHandler('alert', alert))
    updater.dispatcher.add_handler(CommandHandler('password', password))
    updater.dispatcher.add_handler(CommandHandler('remove', remove))

    updater.dispatcher.add_handler(MessageHandler(Filters.text, empty))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()






