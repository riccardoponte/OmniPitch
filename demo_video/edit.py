"""
Cuts, voices and subtitles the demo into a single 1080p MP4 (< 2 minutes).

Inputs (build/): match.webm + markers.json (record.py), title/mcp/closing.webm (cards.py),
narration MP3s (narration.py). Output: demo_video/OmniPitch_demo.mp4
"""
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

from narration import SCENES, duration

ROOT = Path(__file__).parent
BUILD = ROOT / "build"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30

GOAL_TRANSLATION = "YES! GOAL! Tobias Thorne! What joy! Avalon City 2–0 Solaria Rovers!"


def run(args):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def cut(src: Path, start: float, length: float, out: Path):
    run(["-ss", f"{start:.2f}", "-i", str(src), "-t", f"{length:.2f}",
         "-vf", f"fps={FPS},scale=1920:1080:flags=lanczos,format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)])


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_caption(text: str, max_chars: int = 84):
    """Splits narration into subtitle chunks at sentence/clause boundaries."""
    words, chunks, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
        if cur.endswith((".", "?", "!")) and len(cur) > 40:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    return chunks


async def italian_goal(text: str, path: Path):
    await edge_tts.Communicate(text, "it-IT-DiegoNeural", rate="+12%", pitch="+8Hz", volume="+10%").save(str(path))


def main():
    m = json.loads((BUILD / "markers.json").read_text(encoding="utf-8"))
    mk = m["markers"]
    narr = json.loads((BUILD / "narration.json").read_text())
    match = BUILD / "match.webm"

    goal_mp3 = BUILD / "goal_it.mp3"
    asyncio.run(italian_goal(m["goal_line_it"], goal_mp3))
    goal_len = duration(goal_mp3)

    # (name, source, start, length, [(audio, offset_in_segment, caption)])
    s3_len = (mk["goal_it"] - mk["s3_start"]) + goal_len + 0.8
    plan = [
        ("01_title", BUILD / "title.webm", 0.4, 11.0, [("s1_title", 0.6, None)]),
        ("02_live", match, mk["s2_start"] + 0.3, 14.2, [("s2_live", 0.3, None)]),
        ("03_fan", match, mk["s3_start"], s3_len, [("s3_fan", 0.3, None),
                                                  ("goal_it", mk["goal_it"] - mk["s3_start"] + 0.15, GOAL_TRANSLATION)]),
        ("04_halftime", match, mk["added_time"] - 1.0, (mk["ht_report"] + 6.0) - (mk["added_time"] - 1.0),
         [("s4_halftime", 0.3, None)]),
        ("05_verifier", match, mk["s5_start"], mk["s6_start"] - mk["s5_start"], [("s5_verifier", 0.4, None)]),
        ("06_matchcentre", match, mk["s6_start"], 9.5, [("s6_matchcentre", 0.3, None)]),
        ("07_mcp", BUILD / "mcp.webm", 0.3, 9.5, [("s7_mcp", 0.8, None)]),
        ("08_fulltime", match, mk["ft_report"] + 0.3, 3.5, []),
        ("09_closing", BUILD / "closing.webm", 0.3, 7.6, [("s8_close", 0.5, None)]),
    ]

    seg_dir = BUILD / "segments"
    seg_dir.mkdir(exist_ok=True)
    concat_list, audio_events, subs = [], [], []
    t = 0.0
    for name, src, start, length, audios in plan:
        out = seg_dir / f"{name}.mp4"
        cut(src, start, length, out)
        concat_list.append(f"file '{out.as_posix()}'")
        for audio, offset, caption in audios:
            path = goal_mp3 if audio == "goal_it" else BUILD / f"{audio}.mp3"
            at = t + offset
            audio_events.append((path, at))
            if audio == "goal_it":
                subs.append((at, at + goal_len, f"[Italian commentary] {caption}"))
            else:
                chunks = split_caption(SCENES[audio])
                total_chars = sum(len(c) for c in chunks)
                cursor = at
                for c in chunks:
                    span = narr[audio] * len(c) / total_chars
                    subs.append((cursor, cursor + span, c))
                    cursor += span
        t += length
    total = t
    print(f"total length {total:.1f}s")
    assert total < 119, "video must stay under two minutes"

    (BUILD / "concat.txt").write_text("\n".join(concat_list), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(BUILD / "concat.txt"), "-c", "copy", str(BUILD / "video.mp4")])

    # Voice-over: every clip placed at its absolute time, then mixed
    inputs, filters = [], []
    for i, (path, at) in enumerate(audio_events):
        inputs += ["-i", str(path)]
        delay = int(at * 1000)
        filters.append(f"[{i}:a]aresample=48000,adelay={delay}|{delay}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(audio_events)))
    filters.append(f"{mix}amix=inputs={len(audio_events)}:normalize=0,apad,atrim=0:{total:.2f},"
                   f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    run([*inputs, "-filter_complex", ";".join(filters), "-map", "[aout]", "-c:a", "pcm_s16le", str(BUILD / "voice.wav")])

    srt = "\n".join(f"{i + 1}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n" for i, (a, b, text) in enumerate(subs))
    (BUILD / "captions.srt").write_text(srt, encoding="utf-8")

    # Burned-in captions as ASS on an explicit 1080p canvas; BorderStyle 3 = box in OutlineColour (&HAABBGGRR)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        "Style: Default,Segoe UI Semibold,44,&H00F0F0F0,&H00F0F0F0,&H380B0C0E,&H380B0C0E,0,0,0,0,100,100,0,0,"
        "3,14,0,2,120,120,56,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    def ass_time(x: float) -> str:
        cs = int(round(x * 100))
        h, cs = divmod(cs, 360000)
        mi, cs = divmod(cs, 6000)
        sec, cs = divmod(cs, 100)
        return f"{h}:{mi:02d}:{sec:02d}.{cs:02d}"

    events = "\n".join(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{text}" for a, b, text in subs)
    (BUILD / "captions.ass").write_text(header + events + "\n", encoding="utf-8")

    # Run ffmpeg from the build folder so the subtitles path needs no escaping
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", "video.mp4", "-i", "voice.wav",
                    "-vf", "ass=captions.ass",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-shortest",
                    str(ROOT / "OmniPitch_demo.mp4")], check=True, cwd=BUILD)
    print("written", ROOT / "OmniPitch_demo.mp4")


if __name__ == "__main__":
    main()
