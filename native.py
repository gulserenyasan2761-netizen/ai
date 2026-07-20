import pytchat
import threading
import time
import logging
import re
import socket
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq

# --- AYARLAR ---
VIDEO_ID = "8xBHzbfnAbY"
GROQ_API_KEY = "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"
MESSAGE_DELAY = 3 
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
BAD_WORDS = ["küfür1", "argo1", "küfür2"]

# Timeout ayarları[cite: 3]
socket.setdefaulttimeout(60)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

def clean_and_format(text):
    if not text: return ""
    text = text[:199]
    words_to_censor = BAD_WORDS + ["67", "31"]
    for word in words_to_censor:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub("SANSÜRLENMİŞ", text)
    # Cümle başını büyük yap, gerisini olduğu gibi bırak[cite: 3]
    return text[0].upper() + text[1:] if len(text) > 0 else text

def evaluate_math(text):
    clean_text = text.replace(" ", "")
    if any(op in clean_text for op in ["+", "-", "*", "/"]):
        if all(c.isdigit() or c in "+-*/.()" for c in clean_text):
            try: return str(eval(clean_text, {"__builtins__": None}, {}))
            except: return None
    return None

def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=False)
    return build('youtube', 'v3', credentials=creds)

def get_live_chat_id(youtube, video_id):
    response = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
    if 'items' in response and len(response['items']) > 0:
        return response['items'][0]['liveStreamingDetails'].get('activeLiveChatId')
    return None

def send_message(youtube, live_chat_id, text, delay=MESSAGE_DELAY):
    text = clean_and_format(text)
    time.sleep(delay)
    try:
        youtube.liveChatMessages().insert(
            part='snippet',
            body={'snippet': {'liveChatId': live_chat_id, 'type': 'textMessageEvent', 'textMessageDetails': {'messageText': text}}}
        ).execute()
        logger.info(f"Mesaj: {text}")
    except Exception as e:
        logger.error(f"Mesaj gönderilemedi: {e}")

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
            # Botun kendi mesajlarına yanıt vermesini engelle[cite: 3]
            if c.author.isChatOwner: continue
            
            msg = c.message.strip()
            auth = c.author.name
            
            # Matematik
            math_res = evaluate_math(msg)
            if math_res:
                send_message(youtube, chat_id, math_res)
                continue

            # Kebap Modu
            if msg.lower().startswith("!dürüm"):
                siparis = msg[6:].strip() or "KARIŞIK"
                prompt = f"Sen bir tavuk dürümcüsün. '{siparis}' siparişini aldım de ve '[SİPARİŞ] - [Dürüm CİNSİ] + [İÇECEK]' formatında cevap ver."
                ans = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="openai/gpt-oss-120b").choices[0].message.content
                send_message(youtube, chat_id, f"@{auth} {ans}")
                continue

            # Komutlar
            if msg.lower().startswith("!kel"):
                ans = client.chat.completions.create(messages=[{"role": "user", "content": msg[4:]}], model="openai/gpt-oss-120b").choices[0].message.content
                send_message(youtube, chat_id, f"@{auth} {ans}")

    except Exception as e:
        logger.error(f"Hata: {e}")
        time.sleep(5)
