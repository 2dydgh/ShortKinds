from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np, textwrap, os, re

# =============== 사용자 설정 ===============
# W, H = 1080, 1920         # 세로 9:16
W, H =  720, 1280           # HD 9:16 (옛날 유튜브 표준)
FPS  = 24

FONT_TOP = r"C:\Windows\Fonts\H2HDRM.ttf"   #    HMKMRHD    #    #  H2HDRM
FONT = r"C:\Windows\Fonts\NanumSquareR.ttf"

# 글꼴/스타일
FIXED_FS      = 32
FIXED_FS_TOP  = 68
PAD_X, PAD_Y  = 16, 12
BG_ALPHA      = 0
STROKE_RATIO  = 0.06



# ====== 4컷 자동 분할 옵션 ======
SPLIT_4CUT = True  # 한 장 이미지를 2x2(4컷)로 잘라 사용

# 공통 윗자막 파일 (없으면 생략)
TOP_TEXT_PATH = r"C:\Users\8138\Desktop\bigkinds\text\sk_final\top.txt"

# 입력 미디어
images = [
    # ★ 한 장만 넣어도 됩니다. (예: 1024x1024짜리 이미지)
    r"C:\Users\8138\Desktop\bigkinds\images\sk_final.jpg",
]
texts = [
    r"C:\Users\8138\Desktop\bigkinds\text\sk_final\1.txt",
    r"C:\Users\8138\Desktop\bigkinds\text\sk_final\2.txt",
    r"C:\Users\8138\Desktop\bigkinds\text\sk_final\3.txt",
    r"C:\Users\8138\Desktop\bigkinds\text\sk_final\4.txt"
]
audios = [
    r"C:\Users\8138\Desktop\bigkinds\speech\sk_final\1.mp3",
    r"C:\Users\8138\Desktop\bigkinds\speech\sk_final\2.mp3",
    r"C:\Users\8138\Desktop\bigkinds\speech\sk_final\3.mp3",
    r"C:\Users\8138\Desktop\bigkinds\speech\sk_final\4.mp3"
]

# 출력
out_path = r"C:\Users\8138\Desktop\bigkinds\HD_6832_H2HDRM_NanumSquareR_TOP_Y55_sk_final.mp4"

# ===== 고정 배치 파라미터 =====
TOP_Y        = 55  # 원래 : 75
BOTTOM_Y     = 45
CAP_W_RATIO  = 0.94
TOP_H_RATIO  = 0.22
BOT_H_RATIO  = 0.30
# ============================

# 유효성 검사(파일 존재)
for p in images + texts + audios:
    if not os.path.exists(p):
        raise FileNotFoundError(p)

def load_text(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read().strip()

def contain_resize_size(w, h, box_w, box_h):
    s = min(box_w / w, box_h / h)
    return int(w * s), int(h * s)

# -------- 4컷 분할 함수 (좌상, 우상, 좌하, 우하 순) --------
def split_image_2x2(image_path):
    im = Image.open(image_path).convert("RGB")
    Wsrc, Hsrc = im.size
    # 정확히 2등분(홀수일 경우 아래로 내림)
    w = Wsrc // 2
    h = Hsrc // 2
    # 좌상
    tl = im.crop((0, 0, w, h))
    # 우상
    tr = im.crop((w, 0, Wsrc, h))
    # 좌하
    bl = im.crop((0, h, w, Hsrc))
    # 우하
    br = im.crop((w, h, Wsrc, Hsrc))
    # numpy 배열로 반환 (moviepy ImageClip에 바로 넣기 위함)
    return [np.array(tl), np.array(tr), np.array(bl), np.array(br)]

# =============== 캡션 렌더(실측 줄바꿈) ===============
def render_caption_exact(
    text: str, box_w: int, box_h: int, font_path: str, fs: int,
    PAD_X: int = 16, PAD_Y: int = 12,
    STROKE_RATIO: float = 0.06, BG_ALPHA: int = 0,
    align: str = "left", ellipsis: bool = True,
    margin_px: int = 0, return_meta: bool = False,
):
    box_w = max(40, int(box_w)); box_h = max(40, int(box_h))
    inner_w = max(10, box_w - 2*PAD_X) - margin_px
    inner_h = max(10, box_h - 2*PAD_Y)

    font   = ImageFont.truetype(font_path, fs)
    stroke = max(1, int(fs * STROKE_RATIO))
    line_gap = int(fs * 0.30)

    _dummy = Image.new("RGBA", (10, 10)); _draw = ImageDraw.Draw(_dummy)
    def width_px(s: str) -> int:
        b = _draw.textbbox((0,0), s if s else " ", font=font, stroke_width=stroke)
        return b[2] - b[0]

    CJK = r"[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]"
    token_re = re.compile(rf"(\s+|[A-Za-z0-9_.,;:/\\\-+*=?@#%^&(){{}}<>\[\]'\"`~]+|{CJK})")

    lines, cur, cur_w = [], "", 0
    for para in (text or "").replace("\r","").split("\n"):
        para = para.rstrip("\n")
        if para == "":
            lines.append(cur); cur, cur_w = "", 0
            lines.append(""); continue
        for tok in token_re.findall(para):
            if width_px(tok) > inner_w:
                if cur: lines.append(cur); cur, cur_w = "", 0
                for ch in tok:
                    wch = width_px(ch)
                    if cur == "":
                        if wch <= inner_w: cur, cur_w = ch, wch
                        else: lines.append(ch); cur, cur_w = "", 0
                    else:
                        if cur_w + wch <= inner_w: cur += ch; cur_w += wch
                        else: lines.append(cur); cur, cur_w = ch, wch
                continue
            if cur == "":
                cur, cur_w = tok, width_px(tok)
            else:
                cand = cur + tok
                if width_px(cand) <= inner_w:
                    cur, cur_w = cand, width_px(cand)
                else:
                    lines.append(cur); cur, cur_w = tok, width_px(tok)
    if cur != "" or (not lines): lines.append(cur)

    fitted, h, overflowed = [], 0, False
    for ln in lines:
        bb = _draw.textbbox((0,0), ln if ln else " ", font=font, stroke_width=stroke)
        line_height = bb[3] - bb[1]
        next_h = h + line_height + (line_gap if fitted else 0)
        if next_h <= inner_h: fitted.append(ln); h = next_h
        else:
            overflowed = True
            if ellipsis and fitted:
                last = fitted[-1]; ell = "…"
                def fits(txt):
                    b = _draw.textbbox((0,0), txt if txt else " ", font=font, stroke_width=stroke)
                    return (b[2]-b[0]) <= inner_w
                cand = last
                while cand and not fits(cand + ell): cand = cand[:-1]
                fitted[-1] = (cand + ell) if cand else ell
            break

    tot_h, line_sizes = 0, []
    for ln in (fitted or [" "]):
        b = _draw.textbbox((0,0), ln if ln else " ", font=font, stroke_width=stroke)
        lw, lh = b[2]-b[0], b[3]-b[1]
        line_sizes.append((lw, lh)); tot_h += lh + line_gap
    if fitted: tot_h -= line_gap

    cap_w = box_w; cap_h = min(box_h, max(1, tot_h + 2*PAD_Y))
    img = Image.new("RGBA", (cap_w, cap_h), (0,0,0,0))
    if BG_ALPHA > 0:
        img.alpha_composite(Image.new("RGBA", (cap_w, cap_h), (0,0,0,BG_ALPHA)), (0,0))
    draw = ImageDraw.Draw(img)

    y = PAD_Y
    for (ln, (lw, lh)) in zip(fitted or [" "], line_sizes):
        x = max(PAD_X, (cap_w - lw)//2) if align=="center" else PAD_X
        draw.text((x, y), ln if ln else " ", font=font,
                  fill=(255,255,255,255), stroke_width=stroke, stroke_fill=(0,0,0,255))
        y += lh + line_gap

    if return_meta: return np.array(img), {"overflow": overflowed, "cap_w": cap_w, "cap_h": cap_h}
    return np.array(img)

def render_caption_autofit(text, box_w, box_h, font_path, fs_start, fs_min=28, **kwargs):
    ABS_MIN = 18
    cur_min = min(fs_min, ABS_MIN)
    fs = fs_start
    while fs >= cur_min:
        img_np, meta = render_caption_exact(
            text, box_w, box_h, font_path, fs=fs,
            ellipsis=False, return_meta=True, **kwargs
        )
        if not meta["overflow"]:
            meta["used_fs"] = fs; return img_np, meta
        fs -= 2
    img_np, meta = render_caption_exact(
        text, box_w, box_h, font_path, fs=cur_min,
        ellipsis=False, return_meta=True, **kwargs
    )
    meta["used_fs"] = cur_min; return img_np, meta

# 공통 윗자막 로드
top_text_global = load_text(TOP_TEXT_PATH) if os.path.exists(TOP_TEXT_PATH) else ""

# 비율 → 픽셀
CAP_W = int(W * CAP_W_RATIO)
TOP_H = int(H * TOP_H_RATIO)
BOT_H = int(H * BOT_H_RATIO)

# ---- 4컷 자동 분할 처리 ----
if SPLIT_4CUT and len(images) == 1:
    tiles = split_image_2x2(images[0])  # [TL, TR, BL, BR] numpy arrays
    # moviepy는 np.ndarray도 ImageClip에 바로 사용 가능
    image_sources = tiles
else:
    # 파일 경로 그대로 사용
    image_sources = images

# 길이 확인
assert len(image_sources) == len(texts) == len(audios), "분할 후 개수가 texts/audios와 일치해야 합니다."

shots = []
for img_src, txt_p, aud_p in zip(image_sources, texts, audios):
    audio = AudioFileClip(aud_p); dur = audio.duration

    # 자막 먼저 렌더 (오토피트)
    text_main = load_text(txt_p)
    bot_np, bot_meta = render_caption_autofit(
        text_main, CAP_W, BOT_H, FONT,
        fs_start=FIXED_FS, fs_min=30,
        align="left", PAD_X=PAD_X, PAD_Y=PAD_Y,
        STROKE_RATIO=STROKE_RATIO, BG_ALPHA=BG_ALPHA
    )
    bot_clip = ImageClip(bot_np).set_duration(dur)
    bot_h_used = int(bot_meta["cap_h"])

    top_clip = None; top_h_used = 0
    if top_text_global:
        top_np, top_meta = render_caption_autofit(
            top_text_global, CAP_W, TOP_H, FONT_TOP,
            fs_start=FIXED_FS_TOP, fs_min=40,
            align="center", PAD_X=PAD_X, PAD_Y=PAD_Y,
            STROKE_RATIO=STROKE_RATIO, BG_ALPHA=BG_ALPHA
        )
        top_clip = ImageClip(top_np).set_duration(dur)
        top_h_used = int(top_meta["cap_h"])

    # 이미지가 들어갈 세로 공간 (자막 무침범)
    free_top_y = TOP_Y + (top_h_used if top_clip else 0)
    free_bot_y = H - (bot_h_used + BOTTOM_Y)
    free_h = max(50, free_bot_y - free_top_y)

    base = ColorClip(size=(W, H), color=(0, 0, 0)).set_duration(dur)

    # img_src가 경로(str)일 수도, np.ndarray일 수도 있음
    raw = ImageClip(img_src) if isinstance(img_src, np.ndarray) else ImageClip(img_src)
    new_w, new_h = contain_resize_size(raw.w, raw.h, W, free_h)
    img_y = int(free_top_y + (free_h - new_h) // 2)
    img  = raw.resize(newsize=(new_w, new_h)).set_duration(dur)

    layers = [base, img.set_position(("center", img_y))]

    if top_clip is not None:
        layers.append(top_clip.set_position(((W - top_clip.w)//2, int(TOP_Y))))

    bottom_y = H - bot_clip.h - BOTTOM_Y
    layers.append(bot_clip.set_position(((W - bot_clip.w)//2, int(bottom_y))))

    shot = CompositeVideoClip(layers, size=(W, H)).set_duration(dur).set_audio(audio)
    shots.append(shot)

final = concatenate_videoclips(shots, method="compose")
final.write_videofile(
    out_path,
    fps=FPS, codec="libx264",
    audio=True, audio_codec="aac",
    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "faststart", "-g", str(FPS)],
)
