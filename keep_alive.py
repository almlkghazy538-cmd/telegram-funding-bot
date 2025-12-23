herefrom flask import Flask
from threading import Thread
import time
import requests
import logging

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """تشغيل خادم ويب صغير للحفاظ على البوت نشط"""
    t = Thread(target=run)
    t.start()

def ping_self():
    """إرسال طلبات دورية للحفاظ على النشاط"""
    while True:
        try:
            requests.get("https://your-bot-name.onrender.com")
            print("Pinged self to stay awake")
        except:
            pass
        time.sleep(300)  # كل 5 دقائق
