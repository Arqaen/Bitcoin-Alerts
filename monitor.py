from telegram import Bot as TBot
import requests
import time
import json


def getPrice():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        data = requests.get(url)
        data = data.json()
        price = data['price']
        return int(float(price))
    except:
        pass

try:  
    with open('config.json') as f:
        config = json.load(f)
except:
    print("Error loading config.json")
    exit()

token = config['token']
dbname = config['db']
sleep = config['sleep']
Tbot = TBot(token)

while True:

    price=getPrice() 
    if(price == None):
        time.sleep(sleep)
        continue
        
    print(f"\n\nBitcoin price:{price}")
    print("----------------------\n")
    try:
        with open(f'{dbname}', 'r') as f:        
            data = json.load(f)
            original = data
            data = data["_default"]
    except:
        print("Error loading data")
        time.sleep(sleep)
        continue

    try:
        for i in data:
            chat = data[i]['id']
            print(f"\nId: {chat}\n")

            for d in data[i]['btc']["above"]:
                alert = data[i]['btc']["above"][d]
                alert = int(alert)
                print(alert)
                if price > alert:
                    Tbot.send_message(chat, f'Bitcoin price is above of {alert} the actual price is {price}')
                    del original["_default"][i]['btc']["above"][d]
                    with open(f'{dbname}', 'w') as f:
                        json.dump(original, f, indent=4)
                    break

            for d in data[i]['btc']["below"]:
                alert = data[i]['btc']["below"][d]
                alert = int(alert)
                print(alert)
                if price < alert:
                    Tbot.send_message(chat, f'Bitcoin price is below of {alert} the actual price is {price}')
                    del original["_default"][i]['btc']["below"][d]
                    with open(f'{dbname}', 'w') as f:
                        json.dump(original, f, indent=4)
                    break

            time.sleep(1)
    
    except:
        time.sleep(sleep)
        continue    

    time.sleep(sleep)


