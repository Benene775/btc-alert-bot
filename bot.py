import requests
import time

TOKEN = "7797778540:AAFQ5yGD-2l3bM0rhnO35ID1Y7kvg4u6B7U"  
CHAT_ID = "7530371836"  
BTC_API = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"

def get_btc_price():
    response = requests.get(BTC_API)
    data = response.json()
    return float(data["bpi"]["USD"]["rate"].replace(",", ""))

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}
    requests.get(url, params=params)

last_price = None

while True:
    try:
        btc_price = get_btc_price()
        
        if last_price is not None:
            if btc_price < last_price * 0.98:  # Alerte si BTC chute de 2%
                send_telegram_message(f"⚠️ Bitcoin chute ! Prix actuel : {btc_price}$")
            elif btc_price > last_price * 1.02:  # Alerte si BTC monte de 2%
                send_telegram_message(f"🚀 Bitcoin monte ! Prix actuel : {btc_price}$")
        
        last_price = btc_price
        time.sleep(1800)  # Vérifie toutes les 30 minutes

    except Exception as e:
        print(f"Erreur : {e}")
        time.sleep(60)  # Attends 1 minute en cas d'erreur
