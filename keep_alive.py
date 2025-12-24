from flask import Flask
from threading import Thread
import time
import requests
import logging

app = Flask('')

@app.route('/')
def home():
    return "🤖 Bot is alive and running!"

def run():
    """تشغيل خادم ويب صغير"""
    app.run(host='0.0.0.0', port=8080)

def ping_self():
    """إرسال طلبات دورية للحفاظ على النشاط"""
    while True:
        try:
            # يمكنك تغيير الرابط حسب عنوان خدمتك
            requests.get("https://your-bot-name.onrender.com")
            print(f"✅ [{time.strftime('%H:%M:%S')}] Pinged to stay awake")
        except Exception as e:
            print(f"⚠️ [{time.strftime('%H:%M:%S')}] Ping failed: {e}")
        time.sleep(60)  # كل دقيقة

def keep_alive():
    """بدء خدمات البقاء نشط"""
    # تشغيل خادم الويب
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("✅ Keep-alive server started")
    
    # بدء الـping الدوري (تعليق مؤقت لـRender)
    # t2 = Thread(target=ping_self)
    # t2.daemon = True
    # t2.start()
    # print("✅ Self-ping service started")
