# app/utils/translator.py
import urllib.request
import urllib.parse
import json

def translate_to_hindi(text: str) -> str:
    """
    Translates English text to Hindi using a free, public Google Translate API endpoint.
    If the API call fails, it returns an empty string.
    """
    if not text:
        return ""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=hi&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            res = json.loads(response.read().decode())
            translated = "".join([sentence[0] for sentence in res[0] if sentence[0]])
            return translated.strip()
    except Exception as e:
        print(f"Translation failed for '{text}': {e}")
        return ""
