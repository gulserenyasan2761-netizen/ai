import pytchat
import threading
import time
import logging
import re
import socket
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from groq import Groq

# --- AYARLAR ---
VIDEO_ID = "8xBHzbfnAbY"
GROQ_API_KEY = "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"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
BAD_WORDS = ["küfür1", "argo1", "küfür2"]

socket.setdefaulttimeout(60)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AI İstemci Kurulumu
client = Groq(api_key=GROQ_API_KEY)

def clean_and_format(text):
    if not text: return ""
    text = text[:199]
    words_to_censor = BAD_WORDS + ["67", "31"]
    for word in words_to_censor:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub("SANSÜRLENMİŞ", text)
    return text[0].upper() + text[1:] if len(text) > 0 else text

def get_authenticated_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def get_live_chat_id(youtube, video_id):
    response = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
    return response['items'][0]['liveStreamingDetails'].get('activeLiveChatId')

def send_message(youtube, live_chat_id, text):
    text = clean_and_format(text)
    try:
        youtube.liveChatMessages().insert(
            part='snippet',
            body={'snippet': {'liveChatId': live_chat_id, 'type': 'textMessageEvent', 'textMessageDetails': {'messageText': text}}}
        ).execute()
    except Exception as e:
        logger.error(f"Hata: {e}")

youtube = get_authenticated_service()
chat_id = get_live_chat_id(youtube, VIDEO_ID)

def auto_informer():
    while True:
        send_message(youtube, chat_id, "KelcukMüdüş ve Davuk sipariş hattı hazır. !kel soru, !dürüm sipariş.")
        time.sleep(600)

threading.Thread(target=auto_informer, daemon=True).start()

chat = pytchat.create(video_id=VIDEO_ID)
logger.info("Bot dinliyor...")

while chat.is_alive():
    try:
        for c in chat.get().sync_items():
            if c.author.isChatOwner: continue
            msg = c.message.strip()
            auth = c.author.name
            
            # AI !dürüm Komutu[cite: 7]
            if msg.lower().startswith("!dürüm"):
                siparis = msg[6:].strip() or "KARIŞIK"
                prompt = f"Sen bir tavuk dürümcüsün. '{siparis}' siparişini aldım de ve '[SİPARİŞ] - [Dürüm CİNSİ] + [İÇECEK]' formatında cevap ver."
                ans = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="openai/gpt-oss-120b").choices[0].message.content
                send_message(youtube, chat_id, f"@{auth} {ans}")
                continue

            # AI !kel Komutu[cite: 7]
            if msg.lower().startswith("!kel"):
                ans = client.chat.completions.create(messages=[{"role": "user", "content": msg[4:]}], model="openai/gpt-oss-120b").choices[0].message.content
                send_message(youtube, chat_id, f"@{auth} {ans}")

    except Exception as e:
        logger.error(f"Hata: {e}")
        time.sleep(5)
