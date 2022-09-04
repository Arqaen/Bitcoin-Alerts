from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, DispatcherHandlerStop, ConversationHandler
from telegram import BotCommandScopeAllPrivateChats, InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
import json
from tinydb import table, TinyDB, Query
from tinydb.operations import add

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

def empty(update: Update, context: CallbackContext) -> None:
    return update.message.text

def remove(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Please send me the price of the alert you want to remove")
    dp.add_handler(MessageHandler(Filters.text, removeit))

def removeit(update: Update, context: CallbackContext) -> None:

    status = False
    if update.message.text.isdigit():
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
                    if str(data[i]['btc']['above'][x]) == str(update.message.text):
                        status = True
                        temp["btc"]["above"].pop(x)
                        
                for w in data[i]['btc']['below']:
                    if str(data[i]['btc']['below'][w]) == str(update.message.text):
                        status = True
                        temp["btc"]["below"].pop(w)

        if status == True:
            db.update(temp, tabla.id == str(update.message.chat_id))
            update.message.reply_text("Alert removed")          

        if status == False:
            update.message.reply_text("Alert not found")
        
    else:
        update.message.reply_text("Please send me a number")

    dp.remove_handler(MessageHandler(Filters.text, below))
    return update.message.text

def btc(update: Update, context: CallbackContext) -> None:
    price = getPrice()
    update.message.reply_text(f"The price of bitcoin is {price}")
    
def addwhiltelist(update: Update, context: CallbackContext) -> None:
    if update.message.text == pw:
        print("Password correct")
        db.insert({"id":f"{update.message.chat_id}","btc":{"above":{},"below":{}}})
        
    dp.remove_handler(MessageHandler(Filters.text, below))
    return update.message.text
   
def password(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Please send me the password")
    dp.add_handler(MessageHandler(Filters.text, addwhiltelist))
 
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello, I'm a bot that will alert you when the price of bitcoin is higher or lower than the value you set. To start, type /help")
      
def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("The commands are: \n\n\n/help - To see the list of commands \n\n/start - Start the bot \n\n/btc - Get the price of btc\n\n/alert - Create a new alert\n\n/active - Check the active alerts\n\n/remove - Remove some alert\n")

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

    if str(query.data) == '1':
        dp.add_handler(MessageHandler(Filters.text, above))
    elif str(query.data) == '2':
        dp.add_handler(MessageHandler(Filters.text, below))

def above(update: Update, context: CallbackContext) -> None:
    
    if update.message.text.isdigit():

        price = getPrice()
        if int(update.message.text) < price:
            update.message.reply_text(f"The price is already higher than the value you set (Btc: {price})")

        else:
            print(update.message.text)
            tabla = Query()
            key = getKey('above', update.message.chat_id,update.message.text) 
            if key == -1:
                update.message.reply_text("The alert is already in the list")

            if key != None:
                key = key + 1
            if key == None:
                update.message.reply_text(f"You are not in the whitelist, please contact an admin")

            if key:

                temp = db.get(tabla.id == str(update.message.chat_id))
                temp["btc"]["above"][str(key)] = update.message.text
                db.update(temp, tabla.id == str(update.message.chat_id))

                update.message.reply_text(f"Ok, I will alert you when the price of bitcoin is higher than {update.message.text}")
   
    else:
        update.message.reply_text("Please send me a number")

    dp.remove_handler(MessageHandler(Filters.text, above))
    return update.message.text

def below(update: Update, context: CallbackContext) -> None:
    
    if update.message.text.isdigit():

        price = getPrice()
        if int(update.message.text) > price:
            update.message.reply_text(f"The price is already lower than the value you set (Btc: {price})")

        else:
            print(update.message.text)
            tabla = Query()
            key = getKey('below', update.message.chat_id,update.message.text) 
            if key == -1:
                update.message.reply_text("The alert is already in the list")

            if key != None:
                key = key + 1
            if key == None:
                update.message.reply_text(f"You are not in the whitelist, please contact an admin")

            if key:

                temp = db.get(tabla.id == str(update.message.chat_id))
                temp["btc"]["below"][str(key)] = update.message.text
                db.update(temp, tabla.id == str(update.message.chat_id))

                update.message.reply_text(f"Ok, I will alert you when the price of bitcoin is lower than {update.message.text}")
   
    else:
        update.message.reply_text("Please send me a number")

    dp.remove_handler(MessageHandler(Filters.text, below))
    return update.message.text

def active(update: Update, context: CallbackContext) -> None:
    with open(f'{dbname}', 'r') as f:
        try:
            data = json.load(f)
            data = data["_default"]
        except:
            pass

    for i in data:
        i = str(i)
        if str(data[i]['id']) == str(update.message.chat_id):
            activeAlerts = data[i]['btc']
            text = "Active alerts: \n\nAbove of: \n"

            for x in data[i]['btc']['above']:
                text = text + f"- {data[i]['btc']['above'][x]} \n"
                    
        
            text = text + "\nBelow of: \n"
            for w in data[i]['btc']['below']:
                text = text + f"- {data[i]['btc']['below'][w]} \n"
            update.message.reply_text(text)

        else:
            update.message.reply_text("You don't have any active alerts")
 
def getKey(type, id, text):

    with open(f'{dbname}', 'r') as f:
        try:
            data = json.load(f)
            data = data["_default"]
        except:
            pass

    for i in data:
        i = str(i)
        if str(data[i]['id']) == str(id):
            for x in data[i]['btc'][type]:
                x = str(x)
                if text == data[i]['btc'][type][x]:
                    return -1
            return len(data[i]['btc'][type])

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

def main() -> None:

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('btc', btc))
    updater.dispatcher.add_handler(CommandHandler('active', active))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('alert', alert))
    updater.dispatcher.add_handler(CommandHandler('password', password))
    updater.dispatcher.add_handler(CommandHandler('remove', remove))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()






