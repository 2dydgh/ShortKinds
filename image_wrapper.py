# image_wrapper.py
import os,json
from image_quiz import llama3, gpt_image_1

def generate_images(results, save_dir="./outputs"):
    """
    results: pipeline.run() 출력 (리스트[dict]) 
    save_dir: 이미지 저장 폴더
    """
    os.makedirs(save_dir, exist_ok=True)

    # ✅ 퀴즈 저장용 리스트 초기화
    quizzes = []   # ✅ 리스트 초기화
    quiz_path = os.path.join(save_dir, "quizzes.json")

    for idx, row in enumerate(results, start=1):
        summaries = row.get("summaries", [])
        if not summaries:
            continue

        print(f"\n📰 {row['title']}")

        # (1) 프롬프트 + 퀴즈 생성
        out = llama3(summaries)  
        prompt = out["prompts"]  
        quiz = out["quiz"]

        print("최종 프롬프트:", prompt)
        print("퀴즈:", quiz)

        # (2) 이미지 생성
        filename = os.path.join(save_dir, f"output_{idx}.png")
        gpt_image_1(prompt, size="1024x1024", quality="medium", filename=filename)
        print("    → 이미지 저장 완료:", filename)

        # (3) 퀴즈 저장용 데이터 모으기
        quizzes.append({
            "title": row["title"],
            "quiz": quiz,
            "image_file": filename
        })

    # (4) 모든 퀴즈 JSON 저장
    if quizzes:
        with open(quiz_path, "w", encoding="utf-8") as f:
            json.dump(quizzes, f, ensure_ascii=False, indent=2)
        print(f"\n📒 퀴즈 저장 완료 → {quiz_path}")