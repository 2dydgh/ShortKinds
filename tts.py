# tts.py
import os, re
from google.cloud import texttospeech

import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ISPR_Yong_Ho_Lee\Desktop\RTX9070\secrets\bigkinds-469008-c45254f4c998.json"

# ─────────────────────────────
# TTS 초기 설정
# ─────────────────────────────
client = texttospeech.TextToSpeechClient()

voice = texttospeech.VoiceSelectionParams(
    language_code="ko-KR",
    name="ko-KR-Chirp3-HD-Zephyr",
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=1.0,
    pitch=0.0,
)

PART_PREFIX = re.compile(r"^\s*파트\s*\d+\s*:\s*")

def strip_part_prefix(text: str) -> str:
    return PART_PREFIX.sub("", text).strip()

def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# ─────────────────────────────
# 요약 결과 → MP3 변환
# ─────────────────────────────
def generate_tts(results, save_dir="./outputs"):
    os.makedirs(save_dir, exist_ok=True)

    for art_idx, article in enumerate(results, start=1):
        title_safe = safe_filename(article.get("title", f"article{art_idx}"))
        summaries = article.get("summaries", [])

        for part_idx, sentence in enumerate(summaries, start=1):
            text = strip_part_prefix(sentence)
            if not text.strip():
                continue

            synthesis_input = texttospeech.SynthesisInput(text=text)

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            fname = f"{art_idx:03d}_{part_idx:02d}_{title_safe[:20]}.mp3"
            fpath = os.path.join(save_dir, fname)
            with open(fpath, "wb") as fp:
                fp.write(response.audio_content)

            print(f"  🎧 Saved TTS: {fname}")

    print(f"\n📁 모든 TTS 저장 완료 → {save_dir}")
