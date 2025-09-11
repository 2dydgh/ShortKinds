# app.py
import os
import io
import glob
from pathlib import Path
from datetime import datetime
import contextlib
import streamlit as st

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
st.set_page_config(
    page_title="뉴스→쇼츠 생성기",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# CSS 커스터마이징
st.markdown("""
<style>
    /* 전체 배경과 카드 느낌 */
    .main {
        background-color: #fafafa;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* 헤더 강조 */
    h1 {
        color: #1E88E5;
        font-weight: 800;
    }
    h2 {
    color: #1E88E5;
    font-weight: 700;
    }      
    /* Expander 배경 */
    [data-testid="stExpander"] {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 0.5rem;
        margin-bottom: 0.8rem;
        background: #fff;
    }
    /* 버튼 강조 */
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    /* 카드 스타일 */
    .card {
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        background-color: #ffffff;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ───────────── 로고 및 제목 ─────────────
# st.image("assets/rony.gif", width=100)   # 프로젝트 로고 (assets 폴더에 넣어두면 좋아요)
# 메인 타이틀
st.markdown(
    "<h1 style='text-align: center; color: #6764CA; font-size: 4rem;'>Short Kinds</h1>",
    unsafe_allow_html=True
)

# 그라데이션 구분선
# st.markdown(
#     """
#     <hr style="border: 0; height: 3px; 
#                background: linear-gradient(to right, #6764CA, #2F5CA1); 
#                margin: 20px 0;">
#     """,
#     unsafe_allow_html=True
# )

# 서브 타이틀
st.markdown(
    "<h2 style='text-align: center; color: #2F5CA1; font-size: 2rem;'>🎬 쇼츠 생성기</h2>",
    unsafe_allow_html=True
)

# 설명 문구 (카드 스타일)
st.markdown(
    """
    <div style="text-align: center; 
                background-color: #f8f9fa; 
                padding: 8px; 
                border-radius: 10px; 
                color: #555; 
                font-size: 1.02rem;
                line-height: 1.6;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto 30px auto;
                ">
        뉴스 요약 → 이미지 생성 → TTS 변환 <br>
        원클릭으로 숏폼 콘텐츠를 완성해보세요!
    </div>
    """,
    unsafe_allow_html=True
)

# ───────────── 제목 ─────────────
# st.title("📰 뉴스 → 요약 → 이미지 & 음성(TTS) → 쇼츠 생성기")
# st.caption("뉴스를 요약하고, 자동으로 이미지와 음성을 생성해 숏폼 콘텐츠로 변환합니다.")

# ───────────── 사이드바 ─────────────
with st.sidebar:
    st.header("⚙️ 실행 설정")
    date = st.text_input("📅 기준 날짜 (YYYY-MM-DD)", "2025-08-21")
    max_topics = st.number_input("🗂️ 토픽 수", 1, 10, 1)
    per_topic_docs = st.number_input("📰 토픽당 기사 수", 1, 10, 1)

    st.markdown("---")
    isolate_run = st.checkbox("🆕 매 실행마다 고유 폴더 생성", value=True)
    clear_before = st.checkbox("🧹 실행 전 폴더 비우기", value=False)

    st.markdown("---")
    do_images = st.checkbox("🎨 이미지 생성", value=True)
    do_tts = st.checkbox("🎧 음성(TTS) 생성", value=True)

run_btn = st.button("🚀 실행하기")


log_expander = st.expander("🧾 파이프라인 로그 보기", expanded=False)
diag_box = st.container()
articles_box = st.container()
images_box = st.container()
audios_box = st.container()

if run_btn:
    # ✅ 항상 outputs/ 아래에 저장되도록 고정 (pipeline.py가 outputs/를 강제하기 때문)
    OUTPUTS_ROOT = (ROOT / "outputs").resolve()

    # ✅ 날짜를 포함한 런 폴더명: outputs/{date}_{HH-MM-SS}/
    if isolate_run:
        stamp = datetime.now().strftime("%H-%M-%S")
        run_folder_name = f"{date}_{stamp}"
        run_dir = OUTPUTS_ROOT / run_folder_name
    else:
        run_dir = OUTPUTS_ROOT

    if clear_before and run_dir.exists():
        # 폴더 비우기
        for p in run_dir.glob("*"):
            try:
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    import shutil
                    shutil.rmtree(p)
            except Exception:
                pass

    ensure_dir(run_dir)

    # ── (선택) 원시 기사 진단: 수집이 비는지 먼저 확인
    if HAS_CRAWLER:
        with st.spinner("🔎 원시 기사 수집(진단)..."):
            try:
                raw = collect_articles_with_fallback(
                    date=date,
                    max_topics=int(max_topics),
                    per_topic_docs=int(per_topic_docs),
                )
            except Exception as e:
                raw = []
                diag_box.error(f"원시 기사 수집 오류: {e}")
        total = len(raw)
        status_true = sum(1 for a in raw if a.get("status"))
        no_content = sum(1 for a in raw if not str(a.get("content", "")).strip())
        with diag_box:
            st.subheader("🔬 진단")
            st.write(f"- 총 기사 수: **{total}**")
            st.write(f"- status=True(스킵): **{status_true}**")
            st.write(f"- 본문 없음: **{no_content}**")
            if raw[:3]:
                st.write("샘플 제목:", " | ".join(short(a.get("title","")) for a in raw[:3]))
    else:
        st.info("진단용 crawler import 불가 → 이 단계는 생략합니다.")

    # ── ✅ pipeline.run 실행
    #     pipeline.py는 저장 경로를 'outputs/' + save_name 으로 만드므로,
    #     여기서는 'outputs/' 기준 상대경로를 save_name으로 넘겨야 합니다.
    #     예: save_name = '{run_folder_name}/summaries_{date}.json'
    rel_save_from_outputs = str(Path(run_dir.name) / f"summaries_{date}.json")
    ensure_dir(OUTPUTS_ROOT / run_dir.name)  # 상위 폴더 미리 생성

    with st.spinner("📰 뉴스 수집 & 요약 중..."):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                results = pipeline_run(
                    date=date,
                    max_topics=int(max_topics),
                    per_topic_docs=int(per_topic_docs),
                    save_name=rel_save_from_outputs  # ← outputs/{run_folder_name}/summaries_{date}.json
                )
        except Exception as e:
            st.error(f"pipeline.run 오류: {e}")
            st.stop()
        log_expander.text(buf.getvalue())

    if not results:
        st.warning("📝 결과가 비었습니다. (수집 실패/전부 스킵/본문 없음 등)")
        st.info("※ ‘파이프라인 로그 보기’에서 어떤 기사들이 스킵/누락되었는지 확인하세요.")
        st.stop()

    # ── 기사 & 요약 표시
    with articles_box:
        st.subheader("📝 기사 & 요약 미리보기")
        st.caption(f"이번 실행 저장 위치: {run_dir}")
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

    # ── 이미지 생성 (이번 실행 폴더에 저장)
    if do_images:
        with st.spinner("🎨 이미지 생성 중..."):
            try:
                generate_images(results, save_dir=str(run_dir))
            except Exception as e:
                st.error(f"이미지 생성 오류: {e}")
        with images_box:
            st.subheader("🎨 생성된 이미지 (이번 실행)")
            imgs = list_images(run_dir)
            if not imgs:
                st.warning("이번 실행에서 생성된 이미지가 없습니다.")
            else:
                cols = st.columns(min(4, len(imgs)))
                for idx, img in enumerate(imgs):
                    with cols[idx % len(cols)]:
                        st.image(img, use_container_width=True, caption=Path(img).name)

    # ── TTS 생성 (이번 실행 폴더에 저장)
    if do_tts:
        with st.spinner("🎧 TTS 생성 중..."):
            try:
                maybe = generate_tts(results, save_dir=str(run_dir))  # 반환값 없어도 OK
            except Exception as e:
                st.error(f"TTS 생성 오류: {e}")
                maybe = None
        with audios_box:
            st.subheader("🎧 생성된 음성 (이번 실행)")
            audio_paths = maybe if (isinstance(maybe, list) and maybe) else list_audios(run_dir)
            if not audio_paths:
                st.warning("이번 실행에서 생성된 MP3가 없습니다.")
            else:
                for k, a in enumerate(audio_paths, start=1):
                    with open(a, "rb") as f:
                        st.audio(f.read(), format="audio/mp3", start_time=0)
                    st.caption(Path(a).name)

    st.success(f"🎉 완료! 이번 실행 폴더: `{run_dir}`")
else:
    st.info("사이드바 설정 확인 후 **[🚀 실행]**을 눌러주세요.")
