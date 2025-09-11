from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import os

def make_short(results, save_dir="./outputs", output_file="short.mp4"):
    clips = []

    for idx, item in enumerate(results):
        text = item["summary"]  # 요약문 (문장 단위라 가정)

        # 저장된 파일 경로 (generate_images, generate_tts에서 동일 네이밍 규칙 필요)
        img_path = os.path.join(save_dir, f"image_{idx}.png")
        audio_path = os.path.join(save_dir, f"tts_{idx}.mp3")

        # 오디오 불러오기
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration  # 오디오 길이 = 클립 길이

        # 이미지 클립 (오디오 길이에 맞춰 duration 설정)
        img_clip = ImageClip(img_path).set_duration(duration)

        # 이미지에 오디오 붙이기
        final_clip = img_clip.set_audio(audio_clip)

        clips.append(final_clip)

    # 모든 문장 클립 연결
    video = concatenate_videoclips(clips, method="compose")
    out_path = os.path.join(save_dir, output_file)
    video.write_videofile(out_path, fps=24)

    print(f"🎬 숏폼 영상이 생성되었습니다: {out_path}")
