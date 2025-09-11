# pipeline.py
import json, os
from dateutil import parser
from crawler import collect_articles_with_fallback
from summarize import summarize_in_parts

def clean_date(raw_date: str) -> str:
    """ISO8601 날짜를 YYYY-MM-DD로 변환"""
    try:
        dt = parser.parse(raw_date)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return raw_date   # 실패 시 원본 반환

def run(date="2025-08-23", max_topics=50, per_topic_docs=2, save_name=None):
    # ✅ outputs 폴더 자동 생성
    os.makedirs("outputs", exist_ok=True)

    # ✅ date 기반 파일명 자동 생성
    if save_name is None:
        save_name = f"summaries_{date}.json"

    save_path = os.path.join("outputs", save_name)

    # ✅ 1. 오늘 기사 수집
    articles = collect_articles_with_fallback(
        date=date,
        max_topics=max_topics,
        per_topic_docs=per_topic_docs
    )

    results = []  # ← 저장할 리스트

    # ✅ 2. 기사 요약
    for art in articles:
        if art.get("status"):  # 스킵된 기사 건너뜀
            continue

        print("=" * 100)
        print("📰 기사 정보 📰")
        print("기사 ID:", art.get("news_id", ""))
        print("제목:", art.get("title", ""))
        print("언론사:", art.get("provider", ""))
        print("카테고리:", art.get("category", "없음"))
        print("날짜:", clean_date(art.get("published_at", "")))
        print("URL:", art.get("url", ""))
        # print("출처:", art.get("source", ""))
        print()

        content = art.get("content", "")
        if not content.strip():
            print("본문 없음 → 요약 스킵\n")
            continue

        # ✅ 덩어리별 요약
        summaries = summarize_in_parts(content, parts=4)
        for s in summaries:
            print(s, "\n")

        # ✅ 저장할 데이터 구조
        results.append({
            "news_id": art.get("news_id", ""),
            "title": art.get("title", ""),
            "provider": art.get("provider", ""),
            "category": art.get("category", "없음"),
            "published_at": clean_date(art.get("published_at", "")),
            "url": art.get("url", ""),
            # "source": art.get("source", ""),
            "summaries": summaries,
            # "prompts": [f"뉴스 기사 요약: {s}. 이 내용을 나타내는 이미지를 만들어줘." for s in summaries]
        })

    # ✅ JSON 파일 저장
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 저장 완료: {save_path}")
    return results   # ✅ 결과 리스트 리턴

if __name__ == "__main__":
    run()
