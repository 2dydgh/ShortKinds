# image.py
import json
from openai import OpenAI
import base64
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login


def llama3(news_summary):
    # 허가받은 HF Access Token 입력
    token = "your_key"
    if token:
        try:
            login(token)
        except Exception:
            pass

    model_id = "meta-llama/Llama-3.1-8B-Instruct"

    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True, token=token)

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"             # 여러 GPU면 자동 분산
    )

    system_msg = (
            "You are an expert prompt writer for image generation models. "
            "Write a single, concise English prompt optimized for GPT-Image 1 "
            "to generate a 1024x1024 cartoon-style illustration based on the user's news summary. "
            "Embed all constraints directly in the prompt. "
            "Return ONLY the prompt text, no explanations."
        )

    user_msg = (
            f"News summary:\n{news_summary}\n\n"
            "Requirements for the prompt you will write:\n"
            "- Cartoon style, 1024x1024.\n"
            "- Simple, clean background.\n"
            "- No text, no logos, no watermarks.\n"
            "- No blur; crisp details.\n"
            "- No extra fingers; realistic hand anatomy.\n"
            "- Cohesive lighting and color harmony.\n"
            "- Do not mention camera brands or technical metadata.\n"
            "Output only the final prompt."
        )

    messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]

    chat = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer(chat, return_tensors="pt").to(model.device)

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=300,         # 모델이 새로 생성할 최대 토큰 수
            do_sample=True,             # False --> 모델이 가장 높은 확률의 단어만 고름 (프롬프트가 반복적/뻣뻣함), True --> 확률적 샘플링으로 매번 다른 창의적인 결과 도출
            temperature=0.7,            # 1.0 = 원본 확률 그대로, <1.0 = 높은 확률에 더 큰 가중치 (뒷 말에 뭐가 올지 각 단어 확률에 대해서)
            top_p=0.9,                  # 출력 후보 중 확률 누적 합이 p가 될때의 상위 토큰만 남기고 나머진 버림
            repetition_penalty=1.05     # 모델이 같은 단어를 반복하는 걸 막기 위한 패널티, 높을 수록 패널티 강함
        )

    # 신규 생성 부분만 디코딩
    new_tokens = out[0, inputs["input_ids"].shape[-1]:]      # 0~입력 프롬프트는 버리고 새로 생성한 프롬프트만 추출
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()    # 특수 토큰 및 공백 제거

    # 간단한 후처리: 따옴표/코드블럭 제거 가능
    text = text.strip().strip('"').strip("'").strip()       # ""나 '', ... 와 같은 포맷 제거

    print("프롬프트 생성 완료!!")
    print("prompt: ", text)

    return text

def gpt_image_1(p, s: str="1024x1024", q: str="medium", save_path: str=None):
    client = OpenAI(api_key="your_key")

    # 터미널에서 등록하는 게 안전 --> setx OPENAI_API_KEY "sk-xxxx"
    # client = OpenAI()

    """
    GPT-Image-1을 이용해 이미지 생성
    p: 프롬프트
    s: 이미지 크기 (256x256, 512x512, 1024x1024)
    q: 품질 (low, medium, high, auto)
    save_path: 파일 저장 경로 (None이면 저장하지 않음)
    """

    result = client.images.generate(
        model="gpt-image-1",
        prompt=p,
        size=s,   # 옵션: 256x256, 512x512, 1024x1024
        quality=q,      # "low", "medium", "high", "auto"
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    if save_path:
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        print(f"이미지 저장 완료 → {save_path}")

    return result.data[0].url   # URL도 반환


# # 📌 JSON 파일에서 불러오기 (앞에서 저장해둔 summaries.json)
# with open("summaries_son.json", "r", encoding="utf-8") as f:
#     results = json.load(f)

# # JSON 안에 여러 개가 있으면 for문으로 돌 수 있음
# for idx, row in enumerate(results, start=1):
#     summaries = row.get("summaries", [])
#     if not summaries:
#         continue

#     print(f"\n📰 {row['title']}")

#     # summaries 안에 문장 단위로 이미지 생성
#     for s_idx, summary in enumerate(summaries, start=1):
#         print(f"\n  ▶ 파트 {s_idx}: {summary}")

#         # (1) 요약문 → 프롬프트 생성
#         prompt = llama3(summary)
#         print("    최종 프롬프트:", prompt)

#         # (2) 파일명 생성 (뉴스 idx + 파트 번호)
#         save_path = f"output_{idx}_{s_idx}.png"

#         # (3) 프롬프트 → 이미지 생성
#         url = gpt_image_1(
#             p=prompt,
#             s="1024x1024",
#             q="medium",
#             save_path=save_path
#         )

#         print("    → 생성된 이미지 저장:", save_path)
#         print("    → 생성된 이미지 URL:", url)

def generate_images(results, save_dir="./outputs"):
    os.makedirs(save_dir, exist_ok=True)
    
    for idx, row in enumerate(results, start=1):
        summaries = row.get("summaries", [])
        if not summaries:
            continue

        print(f"\n📰 {row['title']}")
        for s_idx, summary in enumerate(summaries, start=1):
            print(f"\n  ▶ 파트 {s_idx}: {summary}")

            prompt = llama3(summary)
            print("    최종 프롬프트:", prompt)

            save_path = os.path.join(save_dir, f"output_{idx}_{s_idx}.png")
            url = gpt_image_1(
                p=prompt,
                s="1024x1024",
                q="medium",
                save_path=save_path
            )

            print("    → 생성된 이미지 저장:", save_path)
            print("    → 생성된 이미지 URL:", url)