import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
ai = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def text_of(msg):
    parts = [b.text for b in msg.content if b.type == "text"]
    if not parts:
        raise RuntimeError(f"no text in reply (stop_reason={msg.stop_reason})")
    return "\n".join(parts).strip()
