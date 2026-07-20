import pytchat
import threading
import time
import logging
import random
import socket
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq

# --- AYARLAR ---
VIDEO_ID = "8xBHzbfnAbY"
GROQ_API_KEY = "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"
MESSAGE_DELAY = 3 
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
BAD_WORDS = ["yarrak", "sik", "porno", "yarrak"]

# Httpx/API zaman aşımı hatalarını azaltmak için soket timeout ayarı[cite: 3]
socket.setdefaulttimeout(60)

# Oyun Modu Değişkenleri
game_active = False
registered_players = {}
current_round_pool = []

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

def clean_and_truncate_text(text):
    text = text[:199]
    for word in BAD_WORDS:
        text = text.replace(word, "sansürlenmiş")
    return text

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
    text = clean_and_truncate_text(text)
    time.sleep(delay)
    try:
        youtube.liveChatMessages().insert(
            part='snippet',
            body={'snippet': {'liveChatId': live_chat_id, 'type': 'textMessageEvent', 'textMessageDetails': {'messageText': text}}}
        ).execute()
        logger.info(f"Mesaj gönderildi: {text}")
    except Exception as e:
        logger.error(f"Mesaj gönderilemedi: {e}")

# --- BOT BAŞLATMA ---
youtube = get_authenticated_service()
chat_id = get_live_chat_id(youtube, VIDEO_ID)

if not chat_id:
    logger.error("Canlı yayın sohbeti bulunamadı!")
    exit()

def auto_informer():
    while True:
        send_message(youtube, chat_id, "Verity/FrameAIsorularınızı cevaplamaya hazır. !vtfr yazarak soru sorabilirsiniz.")
        time.sleep(600)

threading.Thread(target=auto_informer, daemon=True).start()

# --- SOHBET DİNLEME ---
chat = pytchat.create(video_id=VIDEO_ID)
logger.info("Bot yayını dinliyor...")

while chat.is_alive():
    try:
        for c in chat.get().sync_items():
            # Botun kendi mesajlarına yanıt vermesini engelle[cite: 3]
            if c.author.isChatOwner:
                continue

            message_content = c.message.strip()
            author_name = c.author.name
            
            # 1. Matematik Kontrolü
            math_result = evaluate_math(message_content)
            if math_result is not None:
                send_message(youtube, chat_id, math_result)
                continue

            # 2. Oyun Komutları
            if message_content.startswith("!kelgame_oyun:"):
                game_active = True
                game_name = message_content.split(":", 1)[1].strip()
                send_message(youtube, chat_id, f"Oyun: {game_name}. !katıl_oyun:takmaisim ile katılın.")
                continue

            elif message_content.startswith("!katıl_oyun:") and game_active:
                registered_players[author_name] = message_content.split(":", 1)[1].strip()
                send_message(youtube, chat_id, f"Seni kaydettim {author_name}")
                continue

            elif message_content == "!oyun_bitir":
                game_active = False
                registered_players.clear()
                send_message(youtube, chat_id, "Oyun modu kapatıldı.")
                continue

            # 3. Genel Soru (!kel)
            elif message_content.lower().startswith("!vtfr"):
                query = message_content[4:].strip()
                if not query: continue
                try:
                    completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": query}],
                        model="openai/gpt-oss-120b",
                    )
                    reply = f"@{author_name} {completion.choices[0].message.content}"
                    send_message(youtube, chat_id, reply)
                except Exception as e:
                    logger.error(f"GroQ hata: {e}")
    except Exception as e:
        logger.error(f"Sohbet hatası: {e}")
        time.sleep(5) # Hata sonrası bekleme[cite: 3]
