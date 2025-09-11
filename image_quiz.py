import torch
import os
import json
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login


def _safe_json_extract(s: str) -> str:
    """문자열에서 첫 '{' ~ 마지막 '}'까지 잘라 JSON만 추출."""
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON block not found in model output.")
    return s[start:end+1]


def llama3(news_summaries):
    """
    입력:
      - news_summaries: 리스트[str] (각각 뉴스 요약문)
    출력:
      {
        "prompts": [prompt_1, prompt_2, prompt_3, prompt_4],
        "quiz": {language, difficulty, questions:[{question, options[A-D], answer, explanation}]}
      }
    """
    assert isinstance(news_summaries, (list, tuple)) and len(news_summaries) >= 1, \
        "news_summaries는 최소 1개 이상의 문자열을 담은 리스트/튜플이어야 합니다."

    # 허가받은 HF Access Token 입력
    token = "your_key"
    if token:
        try:
            login(token)
        except Exception:
            pass

    model_id = "meta-llama/Llama-3.1-8B-Instruct"
    # model_id = "meta-llama/Llama-3.2-1B"
    # model_id = "meta-llama/Llama-3.2-3B-Instruct"

    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"             # 여러 GPU면 자동 분산
    )

    seed = 42
    torch.manual_seed(seed)

    gen_kwargs = dict(
        do_sample=True,                         # False --> 모델이 가장 높은 확률의 단어만 고름 (프롬프트가 반복적/뻣뻣함), True --> 확률적 샘플링으로 매번 다른 창의적인 결과 도출
        temperature=0.7,                        # 1.0 = 원본 확률 그대로, <1.0 = 높은 확률에 더 큰 가중치 (뒷 말에 뭐가 올지 각 단어 확률에 대해서)
        top_p=0.9,                              # 출력 후보 중 확률 누적 합이 p가 될때의 상위 토큰만 남기고 나머진 버림
        repetition_penalty=1.05,                # 모델이 같은 단어를 반복하는 걸 막기 위한 패널티, 높을 수록 패널티 강함
        max_new_tokens=300,                     # 모델이 새로 생성할 최대 토큰 수
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    gen_quiz_kwargs = dict(
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
        max_new_tokens=350,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )


    system_msg_prompt = (
        "You are an expert prompt writer for image generation models. "
        "Write a single, concise English prompt optimized for GPT-Image 1 "
        "Create a single 1024x1024 cartoon-style illustration laid out as a 2x2 four-panel comic (no text, no logos).\n"
        "The four panels must be tightly packed together with NO gutters, NO borders, and NO spacing between them."
        "Global style for all panels: simple clean backgrounds, consistent lighting, crisp details, realistic hand anatomy, no watermarks.\n"
        "Each panel should visually represent its corresponding summary. "
        "The prompt must transform the meaning of the news summary into a faithful, context-aware visual scene. "
        "Do NOT default to generic symbols unless explicitly implied by the summary such as calendars, clocks, countdown numbers, podiums, arrows, or random cityscapes. "
        "Do NOT use plants, flowers, trees, seeds, sprouts, or nature metaphors for 'growth' or 'innovation or ecosystem"
        "Instead, analyze the actual context and depict it visually and concretely. "
        "Do Not represent a specific quantity or precise amount, exact number, precise amount, numerical value in the image."

        "Panel A (top-left): Illustrate the essence of Summary 1.\n"
        f"Summary 1:\n{news_summaries[0]}\n\n"

        "Panel B (top-right): Illustrate the essence of Summary 2.\n"
        f"Summary 2:\n{news_summaries[1]}\n\n"

        "Panel C (bottom-left): Illustrate the essence of Summary 3.\n"
        f"Summary 3:\n{news_summaries[2]}\n\n"

        "Panel D (bottom-right): Illustrate the essence of Summary 4.\n"
        f"Summary 4:\n{news_summaries[3]}\n\n"

        "Do not render any words, digits, or symbols inside the artwork; rely on visual metaphors only. "
        "Keep composition unified across panels."
        )

    user_msg_prompt = (
        f"News summaries:\n{news_summaries}\n\n"
        "Write only the final optimized prompt. "
        "Do not include explanations or formatting, just the direct prompt text."
    )

    messages = [
        {"role": "system", "content": system_msg_prompt},
        {"role": "user", "content": user_msg_prompt}
    ]
    chat = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat, return_tensors="pt", padding=True).to(model.device)

    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)

    new_tokens = out[0, inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    text = text.strip().strip('"').strip("'").strip()


    print("프롬프트 생성 완료!!")
    print("prompt: ", text)

    combined_summary = "\n".join([f"{i+1}) {s}" for i, s in enumerate(news_summaries)])

    QUIZ_SYSTEM = (
        "You are a precise quiz generator. "
        "Create ONLY multiple-choice questions with exactly four options (0–3). "
        "Return STRICT JSON. No extra commentary."
    )

    QUIZ_SCHEMA = {
      "language": "ko",
      "topic": "string",
      "questions": [
        {
          "type": "mcq",
          "question": "string (Korean)",
          "options": ["0","1","2","3"],
          "answer": "0|1|2|3",
          "explanation": "1-2 sentences (Korean)"
        }
      ]
    }

    quiz_user = f"""
[Task]
Generate EXACTLY ONE multiple-choice quiz question in Korean that REQUIRES synthesizing information across ALL of the following news summaries.

[Summary]
{combined_summary}

[Hard Requirements]
- language: ko
- type: mcq ONLY (no true/false, no short answer).
- The single question MUST require information from AT LEAST TWO different summaries; questions answerable from a single summary are FORBIDDEN.
- The JSON MUST contain a single-item array in "questions" (length == 1).
- Focus on the main issues or keyword in the summaries.
- DO NOT ask about trivial or vague time/ordinal expressions
- Question ("question") must be concise, in Korean.
- Each set of options ("options") must contain exactly 4 items: A, B, C, D.
- **Each option must be ONE SINGLE WORD (no spaces, hyphens, or symbols).**
- The answer field ("answer") must be one of "A","B","C","D".
- Randomize the position of the correct option; do NOT always place the correct answer at A.
- Each question must include a short explanation (1 sentence, in Korean).
- Avoid ambiguity. Base strictly on the summary facts.
- Do Not ask a specific quantity or precise amount, exact number, precise amount.

- DO NOT include any text outside the JSON.

[JSON Schema]
{json.dumps(QUIZ_SCHEMA, ensure_ascii=False, indent=2)}
""".strip()

    quiz_messages = [
        {"role": "system", "content": QUIZ_SYSTEM},
        {"role": "user", "content": quiz_user}
    ]
    quiz_chat = tokenizer.apply_chat_template(quiz_messages, tokenize=False, add_generation_prompt=True)
    quiz_inputs = tokenizer(quiz_chat, return_tensors="pt").to(model.device)

    with torch.no_grad():
        quiz_out = model.generate(
            **quiz_inputs,
            **gen_quiz_kwargs
        )

    quiz_new_tokens = quiz_out[0, quiz_inputs["input_ids"].shape[-1]:]
    quiz_text_raw = tokenizer.decode(quiz_new_tokens, skip_special_tokens=True).strip()

    # JSON 파싱 + 안전 보정
    try:
        quiz_json = _safe_json_extract(quiz_text_raw)
        quiz_data = json.loads(quiz_json)
    except Exception:
        cleaned = quiz_text_raw.strip().strip("`").strip()
        quiz_data = json.loads(_safe_json_extract(cleaned))


    # 후처리 및 검증
    def _fix_one(q):
        q["type"] = "mcq"
        opts = q.get("options", [])
        if isinstance(opts, dict):
            opts = [opts.get("A",""), opts.get("B",""), opts.get("C",""), opts.get("D","")]
        opts = (list(opts) + [""]*4)[:4]
        q["options"] = [str(x).strip()[:160] for x in opts]
        ans = str(q.get("answer","A")).strip().upper()
        if ans not in ["A","B","C","D"]:
            ans = "A"
        q["answer"] = ans
        exp = q.get("explanation","")
        q["explanation"] = str(exp).strip()[:300]
        return q

        # ✅ 정답 위치 재배치(항상 A가 되는 문제 방지)
    LETTERS = ["A", "B", "C", "D"]

    def _rebalance_answer(q, idx=None):
        """
        q: {"question": str, "options": [4], "answer": "A|B|C|D"}
        idx: 문항 인덱스(0-base). 주지 않으면 질문 텍스트 해시로 결정적 분산.
        - 정답이 항상 A가 되지 않도록, 정답 옵션을 다른 위치로 스왑한다.
        """
        opts = list(q.get("options", []))
        ans = q.get("answer", "A")
        if len(opts) != 4 or ans not in LETTERS:
            return q

        # 원하는 목표 위치 선택 (결정적 분산)
        if idx is not None:
            desired = LETTERS[idx % 4]
        else:
            h = sum(ord(c) for c in q.get("question", ""))
            desired = LETTERS[h % 4]

        if desired == ans:
            return q

        i_cur = LETTERS.index(ans)
        i_des = LETTERS.index(desired)
        opts[i_cur], opts[i_des] = opts[i_des], opts[i_cur]
        q["options"] = opts
        q["answer"] = desired
        return q

    quiz_data["language"] = "ko"
    quiz_data["questions"] = [_fix_one(q) for q in quiz_data.get("questions", [])][:1]
    quiz_data["questions"] = [_rebalance_answer(q) for q in quiz_data.get("questions", [])][:1]

    for i, q in enumerate(quiz_data["questions"], 1):
        if q.get("type") != "mcq":
            raise ValueError(f"Q{i}: type must be 'mcq'.")
        if not isinstance(q.get("options"), list) or len(q["options"]) != 4:
            raise ValueError(f"Q{i}: options must have exactly 4 items.")
        if q.get("answer") not in ["A","B","C","D"]:
            raise ValueError(f"Q{i}: answer must be one of A/B/C/D.")

    print("퀴즈 생성 완료!!")
    return {"prompts": text, "quiz": quiz_data}


from openai import OpenAI
import base64
from IPython.display import display, Image as IPyImage
import io


def gpt_image_1(prompts, size: str="1024x1024", quality: str="medium", filename: str=None):
    client = OpenAI(api_key="your_key")

    # 터미널에서 등록하는 게 안전 --> setx OPENAI_API_KEY "sk-xxxx"
    # client = OpenAI()

    if isinstance(prompts, str):
        prompts = [prompts]

    results = []
    for i, p in enumerate(prompts, 1):
        result = client.images.generate(
            model="gpt-image-1",
            prompt=p,
            size=size,
            quality=quality,
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # ✅ 외부에서 파일명을 지정해주면 그걸 사용, 아니면 기본값
        save_path = filename if filename else f"output_{i}.png"

        with open(save_path, "wb") as f:
            f.write(image_bytes)

        display(IPyImage(data=image_bytes))
        print(f"이미지 생성 완료: {save_path}")
        results.append(save_path)

    return results