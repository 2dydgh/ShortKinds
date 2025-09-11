from pipeline import run
from image_wrapper import generate_images
from tts import generate_tts
from shorts import make_shorts

def main():
    # 1. 기사 수집 + 요약
    results = run(date="2025-08-02", max_topics=1, per_topic_docs=1, save_name="summaries0802.json")

    # 2. 요약 → 이미지 생성
    generate_images(results, save_dir="./outputs")

    # 3. 요약 → 음성 생성 (TTS)
    generate_tts(results, save_dir="./outputs")

    # 4. 이미지 + 음성 → 숏폼 영상 생성
    make_shorts(results, save_dir="./outputs", output_file="short0802.mp4")


if __name__ == "__main__":
    main()
