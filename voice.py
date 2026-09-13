import os, requests
from dotenv import load_dotenv

load_dotenv()

VOICE_ID = os.environ["VOICE_ID"]

def speak(text, out="roast.mp3"):
    text = text.replace(". ", '. <break time="0.4s" /> ')
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"],
                 "Content-Type": "application/json"},
        json={"text": text,
              "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.4,
                                 "similarity_boost": 0.75,
                                 "style": 0.6}})
    r.raise_for_status()
    with open(out, "wb") as f:
        f.write(r.content)
    return out