"""
OmniPitch Official Video Tutorial Generator
Combines high-resolution application screenshots, interactive chapter overlays,
synchronized broadcast subtitles, and English synthetic voice narration into a broadcast-quality MP4 video.
"""

import os
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRAIN_DIR = r"C:\Users\pontu\.gemini\antigravity-ide\brain\e0bcd950-0476-42c2-84f1-11064932fdad"
AUDIO_PATH = os.path.join(BASE_DIR, "OmniPitch_Voiceover_EN.wav")
OUTPUT_VIDEO_PATH = os.path.join(BASE_DIR, "OmniPitch_Tutorial_Video.mp4")

# Video Specs
WIDTH = 1920
HEIGHT = 1080
FPS = 24

# Colors
BG_COLOR = (7, 13, 30)
CARD_BG = (15, 23, 42, 230)
BORDER_COLOR = (30, 58, 95)
CYAN = (0, 242, 254)
EMERALD = (16, 185, 129)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)

# Segments / Chapters mapping to Voiceover timing
SEGMENTS = [
    {
        "start": 0.0, "end": 7.5,
        "chapter": "CHAPTER 1: VISION & PLATFORM OVERVIEW",
        "step": "STEP 1 OF 12",
        "img": "home_page_reload_1792257460676.png",
        "subtitle": "Welcome to OmniPitch: Personalized Synthetic Match Intelligence on Microsoft AI.",
    },
    {
        "start": 7.5, "end": 17.0,
        "chapter": "CHAPTER 2: SYNTHETIC TELEMETRY & PROBLEM",
        "step": "STEP 2 OF 12",
        "img": "omnipitch_dashboard_1792253692559.png",
        "subtitle": "In this demonstration, we showcase how high-frequency synthetic football telemetry is transformed into real-time explainable tactical intelligence.",
    },
    {
        "start": 17.0, "end": 25.5,
        "chapter": "CHAPTER 3: LIVE STREAM & KICKOFF ACOUSTICS",
        "step": "STEP 3 OF 12",
        "img": "live_stream_running_1792257702328.png",
        "subtitle": "First, we initiate the live match stream. The acoustic whistle engine synthesizes the match kickoff.",
    },
    {
        "start": 25.5, "end": 34.5,
        "chapter": "CHAPTER 4: TACTICAL PITCH RADAR & PHYSICS",
        "step": "STEP 4 OF 12",
        "img": "top_header_stream_1792257730017.png",
        "subtitle": "On the interactive pitch radar, pass vectors, ball coordinates, and defensive compactness are tracked with sub-second precision.",
    },
    {
        "start": 34.5, "end": 45.0,
        "chapter": "CHAPTER 5: DYNAMIC FORMATION SWITCHER",
        "step": "STEP 5 OF 12",
        "img": "top_stream_header_1792257716151.png",
        "subtitle": "With our tactical system switcher, match analysts can instantly shift formations from 4-3-3 to 4-2-3-1, dynamically recomputing player spatial responsibilities.",
    },
    {
        "start": 45.0, "end": 56.5,
        "chapter": "CHAPTER 6: MULTI-PERSONA BROADCAST NARRATIVE",
        "step": "STEP 6 OF 12",
        "img": "match_stream_live_1792253961927.png",
        "subtitle": "Switching from Analyst to Casual Fan persona, our Narrator agent immediately transforms complex tactical jargon into accessible, high-energy storytelling in four languages.",
    },
    {
        "start": 56.5, "end": 66.0,
        "chapter": "CHAPTER 7: PRO MATCH CENTER - ATTACK MOMENTUM",
        "step": "STEP 7 OF 12",
        "img": "sofascore_attack_momentum_1792254977862.png",
        "subtitle": "In the Pro Match Intelligence Center, the Attack Momentum graph visualizes minute-by-minute dominance and key match events.",
    },
    {
        "start": 66.0, "end": 75.5,
        "chapter": "CHAPTER 8: COMPARATIVE HEAD-TO-HEAD STATS",
        "step": "STEP 8 OF 12",
        "img": "match_statistics_tab_1792257505144.png",
        "subtitle": "Head-to-head comparative analytics display live expected goals, possession splits, and tackles won.",
    },
    {
        "start": 75.5, "end": 84.5,
        "chapter": "CHAPTER 9: ALGORITHMIC RATINGS & MVP CROWN",
        "step": "STEP 9 OF 12",
        "img": "sofascore_ratings_lineups_1792254999522.png",
        "subtitle": "Algorithmic player ratings dynamically evaluate performance from zero to ten, automatically crowning the match MVP.",
    },
    {
        "start": 84.5, "end": 91.5,
        "chapter": "CHAPTER 10: PENALTY SHOT MAP & xG SCALING",
        "step": "STEP 10 OF 12",
        "img": "sofascore_shot_map_1792255010288.png",
        "subtitle": "The penalty shot map charts spatial attempts scaled by expected goal values and shot speeds.",
    },
    {
        "start": 91.5, "end": 98.0,
        "chapter": "CHAPTER 11: INSTANT MATCH REPORT EXPORT",
        "step": "STEP 11 OF 12",
        "img": "match_statistics_active_1792257515426.png",
        "subtitle": "Finally, analysts can export complete match intelligence reports with a single click.",
    },
    {
        "start": 98.0, "end": 100.5,
        "chapter": "CHAPTER 12: GROUNDING VERIFIER & CONCLUSION",
        "step": "STEP 12 OF 12",
        "img": "home_page_1792257450314.png",
        "subtitle": "With an anti-hallucination Grounding Verifier and native Microsoft AI Foundry integration, OmniPitch is engineered for the Grand Prize. Thank you!",
    },
]


def load_font(name: str, size: int):
    candidates = [
        f"C:/Windows/Fonts/{name}.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def build_frame(seg: dict, elapsed_sec: float, total_duration: float, cached_images: dict, fonts: dict) -> Image.Image:
    # 1. Base frame canvas
    frame = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(frame)

    # 2. Draw screenshot content centered with aspect preservation
    img_name = seg["img"]
    if img_name in cached_images:
        src_img = cached_images[img_name]
        # Content viewport area (leaving room for header and bottom subtitles)
        view_x, view_y, view_w, view_h = 40, 75, WIDTH - 80, HEIGHT - 225

        # Resize keeping aspect ratio
        src_w, src_h = src_img.size
        scale = min(view_w / src_w, view_h / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        resized = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center in viewport
        paste_x = view_x + (view_w - new_w) // 2
        paste_y = view_y + (view_h - new_h) // 2

        # Draw sleek card container backdrop
        draw.rectangle(
            [paste_x - 3, paste_y - 3, paste_x + new_w + 3, paste_y + new_h + 3],
            fill=(15, 23, 42),
            outline=BORDER_COLOR,
            width=2,
        )
        frame.paste(resized, (paste_x, paste_y))

    # 3. Top Broadcast Header Bar
    draw.rectangle([0, 0, WIDTH, 65], fill=(7, 13, 30))
    draw.line([0, 65, WIDTH, 65], fill=BORDER_COLOR, width=1)

    # Logo & Brand
    draw.text((45, 18), "⚽ OMNIPITCH", font=fonts["title_bold"], fill=CYAN)
    draw.text((230, 22), "|  PERSONALIZED SYNCHRONIZED TUTORIAL DEMO", font=fonts["sub_medium"], fill=WHITE)

    # Chapter Tag
    draw.rectangle([WIDTH - 580, 16, WIDTH - 220, 50], fill=(18, 30, 58), outline=BORDER_COLOR, width=1)
    draw.text((WIDTH - 565, 24), seg["chapter"], font=fonts["tag_font"], fill=CYAN)

    # Elapsed Time Counter
    mins = int(elapsed_sec // 60)
    secs = int(elapsed_sec % 60)
    tot_mins = int(total_duration // 60)
    tot_secs = int(total_duration % 60)
    time_str = f"⏱️ {mins:02d}:{secs:02d} / {tot_mins:02d}:{tot_secs:02d}"
    draw.text((WIDTH - 200, 23), time_str, font=fonts["time_font"], fill=EMERALD)

    # 4. Bottom Subtitle & Narration Card
    sub_y = HEIGHT - 135
    sub_h = 115
    draw.rectangle([40, sub_y, WIDTH - 40, sub_y + sub_h], fill=(10, 18, 36), outline=CYAN, width=2)

    # Step Badge
    draw.rectangle([55, sub_y + 12, 195, sub_y + 40], fill=CYAN)
    draw.text((65, sub_y + 17), seg["step"], font=fonts["tag_bold"], fill=(7, 13, 30))

    # Narration Title
    draw.text((215, sub_y + 16), "VOICEOVER NARRATION (SYNCHRONIZED ENGLISH AUDIO)", font=fonts["tag_font"], fill=MUTED)

    # Subtitle text wrapped
    lines = wrap_text(seg["subtitle"], fonts["subtitle_font"], WIDTH - 130, draw)
    line_y = sub_y + 46
    for line in lines:
        draw.text((65, line_y), line, font=fonts["subtitle_font"], fill=WHITE)
        line_y += 30

    # 5. Bottom Progress Bar
    progress_pct = min(max(elapsed_sec / total_duration, 0.0), 1.0)
    bar_w = int(WIDTH * progress_pct)
    draw.rectangle([0, HEIGHT - 6, WIDTH, HEIGHT], fill=(20, 30, 50))
    if bar_w > 0:
        draw.rectangle([0, HEIGHT - 6, bar_w, HEIGHT], fill=CYAN)

    return frame


def main():
    print("=== OmniPitch Tutorial Video Generator ===")

    # 1. Check audio duration
    with wave.open(AUDIO_PATH, "r") as w:
        frames_count = w.getnframes()
        rate = w.getframerate()
        total_duration = frames_count / float(rate)
    print(f"Audio Duration: {total_duration:.2f} seconds ({frames_count} frames @ {rate} Hz)")

    total_frames = int(total_duration * FPS)
    print(f"Target Video: {WIDTH}x{HEIGHT} @ {FPS} FPS | Total Video Frames: {total_frames}")

    # 2. Pre-load fonts
    fonts = {
        "title_bold": load_font("segoeuib", 24),
        "sub_medium": load_font("segoeui", 16),
        "tag_font": load_font("segoeuib", 12),
        "tag_bold": load_font("segoeuib", 13),
        "time_font": load_font("JetBrainsMono-Bold", 14),
        "subtitle_font": load_font("segoeuib", 20),
    }

    # 3. Pre-load images
    cached_images = {}
    for seg in SEGMENTS:
        img_name = seg["img"]
        if img_name not in cached_images:
            img_path = os.path.join(BRAIN_DIR, img_name)
            if os.path.exists(img_path):
                cached_images[img_name] = Image.open(img_path).convert("RGB")
                print(f"Loaded asset: {img_name} ({cached_images[img_name].size})")
            else:
                print(f"WARNING: Image not found: {img_path}")

    # 4. Start FFmpeg process piping raw RGB24 frames
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",  # Video from stdin
        "-i", AUDIO_PATH,  # Audio from WAV
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-pix_fmt", "yuv420p",
        "-shortest",
        OUTPUT_VIDEO_PATH,
    ]

    print("Launching FFmpeg encoder...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # 5. Render and pipe frames
    print("Encoding video frames in progress...")
    for frame_idx in range(total_frames):
        elapsed_sec = frame_idx / float(FPS)

        # Find current segment
        current_seg = SEGMENTS[-1]
        for s in SEGMENTS:
            if s["start"] <= elapsed_sec < s["end"]:
                current_seg = s
                break

        # Generate frame
        pil_frame = build_frame(current_seg, elapsed_sec, total_duration, cached_images, fonts)
        raw_bytes = pil_frame.tobytes()
        proc.stdin.write(raw_bytes)

        if frame_idx % 240 == 0 or frame_idx == total_frames - 1:
            pct = (frame_idx / total_frames) * 100
            print(f"Progress: frame {frame_idx}/{total_frames} ({pct:.1f}%) | Time: {elapsed_sec:.1f}s")

    proc.stdin.close()
    stderr_output = proc.stderr.read().decode("utf-8", errors="replace")
    proc.wait()

    if proc.returncode == 0:
        file_size_mb = os.path.getsize(OUTPUT_VIDEO_PATH) / (1024 * 1024)
        print(f"\nSUCCESS! Tutorial video generated at: {OUTPUT_VIDEO_PATH}")
        print(f"Video File Size: {file_size_mb:.2f} MB")
    else:
        print("FFmpeg error occurred:\n", stderr_output)


if __name__ == "__main__":
    main()
