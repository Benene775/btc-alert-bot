import os
import time

import requests

# Le jeton et l'identifiant de conversation ne sont PLUS dans le code : ils y
# étaient en clair, dans un dépôt public, lisibles par n'importe qui. Un jeton
# Telegram permet d'envoyer des messages en se faisant passer pour le bot et de
# lire ce qu'on lui écrit ; des robots parcourent GitHub pour en récolter.
#
# Ils se posent maintenant dans l'environnement :
#     export BTC_BOT_TOKEN="..."   (donné par @BotFather)
#     export BTC_CHAT_ID="..."
# ou dans un fichier .env, que .gitignore empêche de committer.
TOKEN = os.environ.get("BTC_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("BTC_CHAT_ID", "").strip()

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "BTC_BOT_TOKEN et BTC_CHAT_ID doivent être définis dans l'environnement.\n"
        "Voir .env.example."
    )

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
