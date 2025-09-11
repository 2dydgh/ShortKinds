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
st.set_page_config(page_title="Short Kinds", page_icon="🗞️", layout="wide")

# # -------------------------------
# # CSS로 폭 제한 (좁고 가운데 정렬)
# # -------------------------------
# st.markdown(
#     """
#     <style>
#     .block-container {
#         max-width: 700px;
#         margin: 0 auto;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# # -------------------------------
# # 헤더
# # -------------------------------
# st.markdown(
#     """
#     <h1 style='text-align: center; 
#                color: #6764CA; 
#                font-size: 5.5rem; 
#                text-shadow: 2px 2px 8px rgba(0,0,0,0.2);'>
#         Short Kinds
#     </h1>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown(
#     """
#     <div style='text-align: center;'>
#         <div style='color: gray; 
#                     font-size: 1rem; 
#                     background-color: #f9f9ff; 
#                     border: 1px solid #ddd; 
#                     padding: 10px 20px; 
#                     border-radius: 10px; 
#                     box-shadow: 0px 2px 6px rgba(0,0,0,0.1); 
#                     display: inline-block;'>
#             뉴스를 요약하고, 이미지와 TTS로 숏폼 콘텐츠를 만듭니다
#         </div>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown(
#     """
#     <style>
#         /* 전체 배경 */
#         body {
#             background-color: #6764CA;
#         }
#         /* 메인 컨테이너 (본문 영역) */
#         .block-container {
#             background-color: white;
#             padding: 2rem 3rem;
#             border-radius: 20px;
#             box-shadow: 0px 6px 16px rgba(0,0,0,0.15);
#         }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

def inject_app_shell_css():
    st.markdown("""
    <style>
    :root{
      --brand1:#6764CA; --brand2:#2F5CA1; --ink:#23233b; --muted:#6b6b8a;
      --card:#ffffff; --bg:#f5f6ff;
    }
    [data-testid="stAppViewContainer"]{
      background: #5B6AB8;    
      padding: 140px 0 90px; /* 상단 여백 늘림 */
    }
    header[data-testid="stHeader"]{ background: transparent; }
    #MainMenu, footer {visibility:hidden;}

    .block-container{
      max-width: 820px; margin: 0 auto !important;
      background: var(--card); border-radius: 24px;
      box-shadow: 0 18px 48px rgba(16,18,40,.18);
      border: 1px solid rgba(103,100,202,.12);
      padding: 24px 24px 16px;
    }

    .appbar{
    position: fixed; top: 0; left: 0; right: 0; z-index: 999;
    height: 110px;  /* 헤더 높이 늘림 */
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: #99BCE9;
    color: #23233b;
    box-shadow: 0 6px 16px rgba(0,0,0,.25);
    border-bottom: 1px solid rgba(0,0,0,.1);
    }

    .appbar .title{
    font-weight: 700;
    font-size: 3rem;       /* 크게 */
    letter-spacing: -0.5px;
    margin-bottom: 6px;
    color: #fff;    
    }

    .appbar .subtitle{
    font-size: 1rem;
    opacity: .85;
    color: #2c2c54;
    }
    .appbar .logo{
      width: 36px; height: 36px; border-radius: 12px; background: rgba(255,255,255,.15);
      display:flex; align-items:center; justify-content:center; font-size:20px;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.25);
    }


    [data-testid="stTabs"] button[role="tab"]{
      font-weight: 700; color: var(--muted);
      border-radius: 12px 12px 0 0; padding: 10px 16px;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
      color: var(--ink); background: #fff;
      box-shadow: 0 -8px 18px rgba(0,0,0,.06);
      border-bottom: 2px solid transparent;
    }

    .card{ border: 1px solid rgba(0,0,0,.08); border-radius: 16px; padding: 14px 16px; background:#fff;
           box-shadow: 0 8px 20px rgba(0,0,0,.06); }
    .badge{ display:inline-block; padding: 4px 10px; font-size: 12px; border-radius: 999px;
            background:#f4f4ff; color:#47477a; border:1px solid rgba(103,100,202,.25); }
    .section-title{ font-weight:800; font-size:1.15rem; margin: 6px 0 12px; }
    video, audio, img { border-radius: 14px; }
    .stButton>button{
      border-radius: 14px; padding: .8rem 1.2rem; font-weight: 800;
      border: 1px solid rgba(103,100,202,.28);
      box-shadow: 0 10px 24px rgba(103,100,202,.26);
    }
    .card-section{
    margin: 10px 0; padding: 10px 14px;
    border-radius: 20px;
    background: #f9f9ff;
    border: 1px solid rgba(103,100,202,.15);
    box-shadow: inset 0 2px 6px rgba(0,0,0,.05);
    }
    .card-section h3{
    margin-top: 0; margin-bottom: 12px;
    font-weight: 800; font-size: 1.25rem; color: var(--ink);
    }
    .expander-content{
    background: #fff;
    border: 1px solid rgba(0,0,0,.06);
    border-radius: 14px;
    padding: 10px 14px;
    margin-top: 10px;
    }
    .stImage {
    min-height: 300px !important;   /* 원하는 높이 */
    max-height: 300px !important;
    display: flex;
    flex-direction: column;
    justify-content: center;        /* 이미지 세로 가운데 정렬 */
    align-items: center;            /* 이미지 가로 가운데 정렬 */
    }

    /* 이미지 크기를 퍼센트로 줄이기 */
    .stImage img {
        width: 80% !important;      /* 부모 컨테이너 대비 80% */
        height: auto !important;    /* 비율 유지 */
        border-radius: 14px;
        object-fit: contain;        /* 비율 깨지지 않게 */
    }
    </style>
    """, unsafe_allow_html=True)

inject_app_shell_css()

# ===== 앱바(AppBar)
st.markdown("""
<div class="appbar">
    <div class="title">Short Kinds</div>
    <div class="subtitle">뉴스 요약 · 이미지 · TTS · 쇼츠</div>
</div>
""", unsafe_allow_html=True)

# ===== 상단 탭
tabs = st.tabs(["🏠 홈", "📝 요약", "🎧 TTS", "🖼️ 이미지", "🎬 쇼츠"])


st.write("---")
# -------------------------------
# 실행 설정 (메인 입력 폼)
# -------------------------------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.text_input("📅 기준 날짜", "2025-08-21")
    with col2:
        max_topics = st.number_input("🗂️ 토픽 수", 1, 10, 1)
    with col3:
        per_topic_docs = st.number_input("📰 토픽당 기사 수", 1, 10, 1)

    st.markdown(
        """
        <style>
        div.stButton { text-align: center; }  /* 버튼 가운데 정렬 */
        div.stButton > button:first-child {
            background: linear-gradient(90deg,  #99BCE9);
            color: white;
            font-weight: 700;
            font-size: 1.2rem;
            padding: 0.9rem 1.6rem;
            border-radius: 14px;
            border: none;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
            transition: all 0.25s ease-in-out;
        }
        div.stButton > button:first-child:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 28px rgba(0,0,0,0.35);
            background: linear-gradient(90deg, #99BCE9);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 실행 버튼
    run_btn = st.button("실행")

    # (필요하면 유지)
    diag_box = st.container()
    # articles_box/images_box/audios_box는 각 탭에서 다시 만듦

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

        # 다른 탭에서도 접근할 수 있게 세션에 저장
        st.session_state["results"] = results
        st.success("✅ 데이터 로드 완료! 상단 탭에서 결과를 확인하세요.")


    with tabs[1]:
        st.markdown("<div class='section-title'>📝 기사 & 요약 미리보기</div>", unsafe_allow_html=True)
        # st.markdown("<div class='card-section'><h3>📝 기사 & 요약</h3>", unsafe_allow_html=True)
        if "results" not in st.session_state:
            st.info("먼저 홈 탭에서 🚀 실행을 눌러 데이터를 불러오세요.")
        else:
            with st.spinner("⏳ 요약 생성 중..."):
                time.sleep(14)   # 👉 시간을 늘려서 '생성 중' 연출
            results = st.session_state["results"]
            for i, r in enumerate(results, start=1):
                with st.expander(f"[{i:02d}] {r.get('title','')[:60]}…", expanded=(i==1)):
                    st.markdown("<div class='expander-content'>", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"<span class='badge'>언론사</span> {r.get('provider','')}", unsafe_allow_html=True)
                    c2.markdown(f"<span class='badge'>카테고리</span> {r.get('category','없음')}", unsafe_allow_html=True)
                    c3.markdown(f"<span class='badge'>발행일</span> {r.get('published_at','')}", unsafe_allow_html=True)
                    if r.get("url"):
                        st.markdown(f"[원문 보기]({r['url']})")
                    st.markdown("**요약(자막 후보)**")
                    for s in r.get("summaries", []):
                        st.markdown(f"- {s}")
                    st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:  # TTS
        st.markdown("<div class='section-title'>🎧 TTS 미리듣기</div>", unsafe_allow_html=True)
        if "results" not in st.session_state:
            st.info("먼저 홈 탭에서 🚀 실행을 눌러 데이터를 불러오세요.")
        else:
            with st.spinner("⏳ 음성 생성 중..."):
                time.sleep(15)  # 👉 생성 중 연출
            tts_files = ["assets/1.mp3","assets/2.mp3","assets/3.mp3","assets/4.mp3"]
            for i, f in enumerate(tts_files, start=1):
                st.markdown(f"**파트 {i}** 🎤")
                st.audio(f, format="audio/mp3")
                st.write("---")

    with tabs[3]:  # 이미지
        st.markdown("<div class='section-title'>🖼️ 이미지 미리보기</div>", unsafe_allow_html=True)
        if "results" not in st.session_state:
            st.info("먼저 홈 탭에서 🚀 실행을 눌러 데이터를 불러오세요.")
        else:
            with st.spinner("⏳ 이미지 생성 중..."):
                time.sleep(20)
                
            img_files = [
                "assets/hyundai_final_tile1.png",
                "assets/hyundai_final_tile2.png",
                "assets/hyundai_final_tile3.png",
                "assets/hyundai_final_tile4.png",
            ]
            cols = st.columns(2)
            for i, f in enumerate(img_files):
                with cols[i % 2]:
                    st.image(f, use_container_width=True)
                    st.caption(f"🖼️ 이미지 {i+1}")

    with tabs[4]:  # 영상
        st.markdown("<div class='section-title'>🎬 쇼츠 영상 </div>", unsafe_allow_html=True)
        if "results" not in st.session_state:
            st.info("먼저 홈 탭에서 🚀 실행을 눌러 데이터를 불러오세요.")
        else:
            with st.spinner("⏳ 쇼츠 생성 중..."):
                time.sleep(20)
                st.markdown(
                    """
                    <style>
                    video {
                        max-width: 45% !important;   /* 원하는 비율로 줄이기 */
                        height: auto !important;
                        display: block;
                        margin: 0 auto;              /* 가운데 정렬 */
                        border-radius: 16px;         /* 모서리 둥글게 */
                        box-shadow: 0 8px 20px rgba(0,0,0,0.2);
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                st.video("assets/hyundai_final.mp4")
            st.success("🎉 쇼츠 생성 완료!")
