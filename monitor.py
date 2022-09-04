from telegram import Bot as TBot
import requests
import random
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
    
price=getPrice()
Tbot = TBot('5055999648:AAFbbe6lWYAiS3Juxmk2d713h-oaW1ME0VY')
chat = "-1001671121948"

if(price):
    if(price >= up):
        cap=f"Bitcoin price is above of {up} the actual price is {price}"

    elif(price <= down):
        cap=f"Bitcoin price is below of {down} the actual price is {price}"

    Tbot.send_message(chat,text=cap)



