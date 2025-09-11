# fake.py
import os
import json
import io
import glob
from pathlib import Path
from datetime import datetime
import contextlib
import streamlit as st
import time

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

from pipeline import run as pipeline_run
from image_wrapper import generate_images
from tts import generate_tts

try:
    from crawler import collect_articles_with_fallback
    HAS_CRAWLER = True
except Exception:
    HAS_CRAWLER = False

# ───────────── 유틸 ─────────────
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def list_images(dir_path: Path):
    paths = sorted(dir_path.glob("output_*.png"))
    if not paths:
        pats = []
        for p in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            pats += glob.glob(str(dir_path / p))
        paths = list(map(Path, sorted(pats)))
    return [str(p) for p in paths]

def list_audios(dir_path: Path):
    return [str(p) for p in sorted(dir_path.glob("*.mp3"))]

def short(s: str, n=60):
    if not s: return ""
    return s if len(s) <= n else s[:n] + "…"

# ───────────── UI 설정 ─────────────
st.set_page_config(page_title="Short Kinds")

# -------------------------------
# CSS로 폭 제한 (좁고 가운데 정렬)
# -------------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 700px;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# 헤더
# -------------------------------
st.markdown(
    """
    <h1 style='text-align: center; 
               color: #6764CA; 
               font-size: 5.5rem; 
               text-shadow: 2px 2px 8px rgba(0,0,0,0.2);'>
        Short Kinds
    </h1>
    """,
    unsafe_allow_html=True
)

# st.markdown(
#     """
#     <div style='text-align: center;'>
#         <div style='height: 6px; 
#                     margin: 10px auto 30px auto; 
#                     width: 50%; 
#                     background: linear-gradient(to right, #6764CA, #2F5CA1); 
#                     border-radius: 3px;'>
#         </div>
#     </div>
#     """,
#     unsafe_allow_html=True
# )
# st.markdown(
#     """
#     <div style='text-align: center;'>
#         <h2 style='color: #2F5CA1; 
#                    font-size: 2rem; 
#                    display: inline-block;
#                    animation: fadeIn 2s;'>
#             쇼츠 생성기
#         </h2>
#     </div>

#     <style>
#         @keyframes fadeIn {
#             from {opacity: 0;}
#             to {opacity: 1;}
#         }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

st.markdown(
    """
    <div style='text-align: center;'>
        <div style='color: gray; 
                    font-size: 1rem; 
                    background-color: #f9f9ff; 
                    border: 1px solid #ddd; 
                    padding: 10px 20px; 
                    border-radius: 10px; 
                    box-shadow: 0px 2px 6px rgba(0,0,0,0.1); 
                    display: inline-block;'>
            뉴스를 요약하고, 이미지와 TTS로 숏폼 콘텐츠를 만듭니다
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        /* 전체 배경 */
        body {
            background-color: #6764CA;
        }
        /* 메인 컨테이너 (본문 영역) */
        .block-container {
            background-color: white;
            padding: 2rem 3rem;
            border-radius: 20px;
            box-shadow: 0px 6px 16px rgba(0,0,0,0.15);
        }
    </style>
    """,
    unsafe_allow_html=True
)



# st.markdown(
#     "<h1 style='text-align: center; color: #6764CA; font-size: 4rem;'>Short Kinds</h1>",
#     unsafe_allow_html=True
# )
# st.markdown(
#     "<h2 style='text-align: center; color: #2F5CA1; font-size: 2rem;'>쇼츠 생성기</h2>",
#     unsafe_allow_html=True
# )
# st.markdown(
#     "<p style='text-align: center; color: gray; font-size: 1rem;'>뉴스를 요약하고, 이미지와 TTS로 숏폼 콘텐츠를 만듭니다</p>",
#     unsafe_allow_html=True
# )

st.write("---")

# -------------------------------
# 실행 설정 (메인 입력 폼)
# -------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    date = st.text_input("📅 기준 날짜", "2025-08-21")
with col2:
    max_topics = st.number_input("🗂️ 토픽 수", 1, 10, 1)
with col3:
    per_topic_docs = st.number_input("📰 토픽당 기사 수", 1, 10, 1)

# do_images = st.checkbox("🎨 이미지 생성", value=True)
# do_tts = st.checkbox("🎧 음성 생성", value=True)

st.write("---")

# -------------------------------
run_btn = st.button("실행")

# log_expander = st.expander("🧾 파이프라인 로그 보기", expanded=False)
diag_box = st.container()
articles_box = st.container()
images_box = st.container()
audios_box = st.container()

if run_btn:
    json_file = ROOT /  f"summary_{date}.json"

    if not json_file.exists():
        st.error(f"❌ {json_file} 파일이 존재하지 않습니다.")
        st.stop()

    with open(json_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    if not results:
        st.warning("📝 JSON에 내용이 없습니다.")
        st.stop()

    # # ✅ 항상 outputs/ 아래에 저장되도록 고정 (pipeline.py가 outputs/를 강제하기 때문)
    # OUTPUTS_ROOT = (ROOT / "outputs").resolve()

    # # ✅ 날짜 기반 폴더명 (고정, 실행마다 새로 만들고 싶지 않다면 그냥 date만 사용해도 됨)
    # run_folder_name = f"{date}"
    # run_dir = OUTPUTS_ROOT / run_folder_name

    # ensure_dir(run_dir)

    # # ── (선택) 원시 기사 진단: 수집이 비는지 먼저 확인
    # if HAS_CRAWLER:
    #     with st.spinner("🔎 원시 기사 수집(진단)..."):
    #         try:
    #             raw = collect_articles_with_fallback(
    #                 date=date,
    #                 max_topics=int(max_topics),
    #                 per_topic_docs=int(per_topic_docs),
    #             )
    #         except Exception as e:
    #             raw = []
    #             diag_box.error(f"원시 기사 수집 오류: {e}")
    #     total = len(raw)
    #     status_true = sum(1 for a in raw if a.get("status"))
    #     no_content = sum(1 for a in raw if not str(a.get("content", "")).strip())
    #     with diag_box:
    #         st.subheader("🔬 진단")
    #         st.write(f"- 총 기사 수: **{total}**")
    #         st.write(f"- status=True(스킵): **{status_true}**")
    #         st.write(f"- 본문 없음: **{no_content}**")
    #         if raw[:3]:
    #             st.write("샘플 제목:", " | ".join(short(a.get("title","")) for a in raw[:3]))
    # else:
    #     st.info("진단용 crawler import 불가 → 이 단계는 생략합니다.")

    # # ── ✅ pipeline.run 실행
    # #     pipeline.py는 저장 경로를 'outputs/' + save_name 으로 만드므로,
    # #     여기서는 'outputs/' 기준 상대경로를 save_name으로 넘겨야 합니다.
    # #     예: save_name = '{run_folder_name}/summaries_{date}.json'
    # rel_save_from_outputs = str(Path(run_dir.name) / f"summaries_{date}.json")
    # ensure_dir(OUTPUTS_ROOT / run_dir.name)  # 상위 폴더 미리 생성

    # with st.spinner("📰 뉴스 수집 & 요약 중..."):
    #     buf = io.StringIO()
    #     try:
    #         with contextlib.redirect_stdout(buf):
    #             results = pipeline_run(
    #                 date=date,
    #                 max_topics=int(max_topics),
    #                 per_topic_docs=int(per_topic_docs),
    #                 save_name=rel_save_from_outputs  # ← outputs/{run_folder_name}/summaries_{date}.json
    #             )
    #     except Exception as e:
    #         st.error(f"pipeline.run 오류: {e}")
    #         st.stop()
    #     # log_expander.text(buf.getvalue())

    # if not results:
    #     st.warning("📝 결과가 비었습니다. (수집 실패/전부 스킵/본문 없음 등)")
    #     st.info("※ ‘파이프라인 로그 보기’에서 어떤 기사들이 스킵/누락되었는지 확인하세요.")
    #     st.stop()

    # ── 기사 & 요약 표시
    with st.spinner("📰 뉴스 요약 불러오는 중..."):
        time.sleep(20)  # 로딩 연출
        with articles_box:
            st.subheader("📝 기사 & 요약 미리보기")
            # st.caption(f"이번 실행 저장 위치: {run_dir}")
            for i, r in enumerate(results, start=1):
                with st.expander(f"[{i:02d}] {short(r.get('title'))}", expanded=(i == 1)):
                    cols = st.columns(3)
                    cols[0].markdown(f"**언론사**: {r.get('provider','')}")
                    cols[1].markdown(f"**카테고리**: {r.get('category','없음')}")
                    cols[2].markdown(f"**발행일**: {r.get('published_at','')}")
                    if r.get("url"): st.markdown(f"[원문 보기]({r['url']})")
                    st.markdown("**요약(자막 후보)**")
                    for j, s in enumerate(r.get("summaries", []), start=1):
                        st.write(f"💬 {s}")

    # ---------------- 구분선 ----------------
    st.markdown("---")
    st.subheader("🎧 TTS 미리듣기")

    # ── TTS
    with st.spinner("🎧 TTS 음성을 불러오는 중..."):
        time.sleep(20)
        tts_files = [
            "assets/1.mp3",
            "assets/2.mp3",
            "assets/3.mp3",
            "assets/4.mp3",
        ]
        for i, tts_file in enumerate(tts_files, start=1):
            st.markdown(f"**파트 {i}** 🎤")
            st.audio(tts_file, format="audio/mp3")
            st.write("---")  # 구분선
            # st.audio(tts_file, format="audio/mp3")
            # st.caption(f"🎧 파트 {i}")

    # ---------------- 구분선 ----------------
    st.markdown("---")
    st.subheader("🖼️ 이미지 미리보기")

    # ── 이미지
    with st.spinner("🖼️ 이미지 생성 중..."):
        time.sleep(20)
        img_files = [
            "assets/hyundai_final_tile1.png",
            "assets/hyundai_final_tile2.png",
            "assets/hyundai_final_tile3.png",
            "assets/hyundai_final_tile4.png",
        ]
        cols = st.columns(2)  # 2열
        for i, img_file in enumerate(img_files):
            with cols[i % 2]:
                st.image(img_file, use_container_width=True)
                st.caption(f"🖼️ 이미지 {i+1}")

    # with st.spinner("🖼️ 이미지 생성 중..."):
    #     time.sleep(2)
    #     img_files = [
    #         "assets/hyundai_final_tile1.png",
    #         "assets/hyundai_final_tile2.png",
    #         "assets/hyundai_final_tile3.png",
    #         "assets/hyundai_final_tile4.png",
    #     ]
    #     for img_file in img_files:
    #         st.image(img_file, use_container_width=True)
    #         st.caption(f"🖼️ 이미지 {img_file}")

    # ---------------- 구분선 ----------------
    st.markdown("---")
    st.subheader("🎬 쇼츠 영상 미리보기")

    # ── 쇼츠
    with st.spinner("🎬 쇼츠 영상 합성 중..."):
        time.sleep(10)
        st.video("assets/hyundai_final.mp4")
        
    

    st.success(f"🎉 쇼츠 생성 완료!" )
    # st.balloons()
else:
    st.info("▶ 사이드바 설정 확인 후 실행 버튼을 눌러주세요.")
