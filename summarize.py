import re, torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# MODEL = "gogamza/kobart-summarization"  # ✅ KoBART 요약 모델
MODEL = "lcw99/t5-base-korean-text-summary"  # ✅ Kot5 요약 모델
# MODEL = "noahkim/KoT5_news_summarization"


tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL).to(DEVICE).eval()

def clean(x): 
    x = re.sub(r"\[[^\]]+\]", " ", x)   # [기자명], [사진=..] 제거
    x = re.sub(r"\([^)]+\)", " ", x)    # (사진=연합뉴스) 등 제거
    x = re.sub(r"무단 전재.*?금지", " ", x) # 저작권 안내문 제거
    x = re.sub(r"\s+", " ", x)
    return x.strip()

def postprocess(summary: str) -> str:
    summary = re.sub(r"[가-힣]{2,4}\s?기자", "", summary)  # 기자명 제거
    summary = re.sub(r"연합뉴스", "", summary)
    summary = re.sub(r"\s+", " ", summary)
    return summary.strip()

@torch.inference_mode()
def summarize(text,
              max_in=1024, max_out=100, min_out=50,
              beams=5, lp=0.8, no_rep=3, rep_penalty=2.0):
    text = clean(text)  # ✅ KoBART는 prefix 불필요
    inputs = tok([text], truncation=True, max_length=max_in, return_tensors="pt").to(DEVICE)
    ids = model.generate(
        **inputs,
        num_beams=beams,
        # max_new_tokens=120,  # 새로 생성할 최대 토큰 수
        max_length=max_out, 
        min_length=min_out,
        length_penalty=lp,
        no_repeat_ngram_size=no_rep,
        repetition_penalty=rep_penalty,
        early_stopping=True
    )
    return tok.decode(ids[0], skip_special_tokens=True)

# ✅ 텍스트를 n등분으로 나누는 함수
def chunk_text(text, n=4):
    """긴 텍스트를 n 덩어리로 균등 분할"""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    k, m = divmod(len(sentences), n)
    chunks, start = [], 0
    for i in range(n):
        end = start + k + (1 if i < m else 0)
        chunks.append(" ".join(sentences[start:end]))
        start = end
    return chunks

# def chunk_text(text, max_tokens=500): # by tokens
#     """긴 텍스트를 max_tokens 길이로 나누기"""
#     tokens = tok.tokenize(text)
#     chunks = []
#     for i in range(0, len(tokens), max_tokens):
#         chunk = tok.convert_tokens_to_string(tokens[i:i+max_tokens])
#         chunks.append(chunk)
#     return chunks

# ✅ chunk 길이에 따라 min/max 출력 길이 동적 조정
def summarize_dynamic(text):
    length = len(tok.tokenize(text))
    # length = len(text)
    if length < 100:      # 짧은 덩어리
        min_out, max_out = 10, 80
    elif length < 300:    # 중간 길이
        min_out, max_out = 30, 100
    else:                 # 긴 덩어리
        min_out, max_out = 50, 120
    return summarize(text, min_out=min_out, max_out=max_out)
   

# def summarize_dynamic(text):
#     length = len(text)
#     min_out = max(10, int(length * 0.05))   # 원문 길이의 5%
#     max_out = min(200, int(length * 0.15))  # 원문 길이의 15%
#     return summarize(text, min_out=min_out, max_out=max_out)

def clean_for_prompt(text: str) -> str:
    """이미지 프롬프트용 안전 문자열 (따옴표+잡음 제거)"""
    remove_chars = ['"', "'", "“", "”", "‘", "’"]
    for ch in remove_chars:
        text = text.replace(ch, "")
    return text.strip()

# ✅ 덩어리별 요약하기
def summarize_in_parts(text, parts=4):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    total_len = len(text)

    # 🚀 파트 개수 자동 조정
    if len(sentences) < parts:
        parts = max(1, len(sentences))  # 문장 수에 맞게 줄임
    # elif total_len < 500:
    #     parts = min(parts, 2)  # 너무 짧은 기사면 최대 2파트만

    chunks = chunk_text(text, n=parts)
    summaries = []
    for i, chunk in enumerate(chunks, 1):
        if not chunk.strip():
            continue
        summary = summarize_dynamic(chunk)
        summary = clean_for_prompt(summary)
        summary = postprocess(summary)
        summaries.append(f"파트 {i}: {summary}")
    return summaries



if __name__ == "__main__":
    sample = '''
무안군의회가 에너지 전환과 치유농업 정책개발을 위한 연구용역에 본격 착수했다.

17일 무안군의회에 따르면 지난 14일 의회 세미나실에서 의원연구단체 연구용역 착수보고회를 개최했다.

이번 보고회는 지난 6월 발족한 의원연구단체인 ‘에너지 대전환시대 준비 연구회’와 ‘치유농업 정책개발 연구회’가 각각 선정한 연구과제를 본격적으로 추진하기 위해 마련됐다.

보고회에서는 각 연구단체의 의원, 연구책임자, 관계 공무원 등 20여명이 참석한 가운데 연구과제의 목적, 과업수행 방안, 기대효과 등을 논의했다.

에너지 대전환시대 준비 연구회는 지역의 에너지 자립 기반 마련과 이익공유형 에너지 기본소득 모델 구축을 위한 전략 수립을 목표로, 무안군의 재생에너지 활용 방안 및 중장기 로드맵 제시를 중심으로 연구를 진행할 예정이다.

치유농업 정책개발 연구회는 농업과 복지의 융합을 통해 군민 삶의 질 향상을 도모하고자 치유농업의 개념 정립과 무안군 실정에 맞는 정책 모델 개발을 중점적으로 추진할 계획이다.

김원중 에너지 대전환시대 준비 연구회 대표의원은 “이번 연구를 통해 군민 모두가 에너지 혜택을 체감할 수 있는 정책을 마련해 무안군이 에너지 전환시대를 선도하는 지자체로 거듭나길 기대한다”고 말했다.

임윤택 치유농업 정책개발 연구회 대표의원은 “무안군 치유농업이 농업의 다원적 가치 실현과 복지서비스의 새로운 대안으로 자리매김할 수 있도록 정책적 방향성을 제시하겠다”고 밝혔다.

한편 의원연구단체는 이번 착수보고회를 시작으로 관련 분야에 대한 연구를 추진해 12월까지 연구활동에 대한 성과를 도출하고 향후 정책 제안 및 의안 발의 등 정책 활동을 이어갈 방침이다.'''
    
    # print(summarize(sample))
    res = summarize_in_parts(sample, parts=4)
    for r in res:
        print(r, "\n")
