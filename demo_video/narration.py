"""Generates the English voice-over, one MP3 per scene, with Microsoft neural TTS (edge-tts)."""
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

OUT = Path(__file__).parent / "build"
VOICE = "en-GB-RyanNeural"

SCENES = {
    "s1_title": "Football stories don't end at the scoreline. This is OmniPitch: a live football broadcast, "
                "written by AI agents, and fact-checked before it reaches air.",
    "s2_live": "Eight specialised agents share one blackboard. As synthetic match events stream in, they call the "
               "play-by-play, explain why each moment matters, and render broadcast graphics with the evidence "
               "behind every claim.",
    "s3_fan": "Same match, different fan. Switch to Italian, casual mode, and pick your club. "
              "The commentary takes your side, and it speaks.",
    "s4_halftime": "Real match time. Stoppage time is announced, the broadcast pauses at half-time, "
                   "and an automated report explains the first half.",
    "s5_verifier": "Every number and every name is checked by a Grounding Verifier against the event log. "
                   "Across eighty simulated matches, it caught ninety-nine point eight percent of injected "
                   "hallucinations, with zero false alarms.",
    "s6_matchcentre": "Analysts get attack momentum, expected goals, player ratings and a shot map, "
                      "all from the same shared state.",
    "s7_mcp": "Through the Model Context Protocol, any agent, like GitHub Copilot, can query the live match "
              "and ask why a moment mattered.",
    "s8_close": "Designed for Microsoft Foundry and Azure. OmniPitch: every match, made for every fan.",
}


def duration(path: Path) -> float:
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", proc.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def speak(text: str, path: Path, voice: str = VOICE, rate: str = "+4%"):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    durations = {}
    for name, text in SCENES.items():
        path = OUT / f"{name}.mp3"
        await speak(text, path)
        durations[name] = round(duration(path), 2)
    (OUT / "narration.json").write_text(json.dumps(durations, indent=2))
    print(json.dumps(durations, indent=2), "total", round(sum(durations.values()), 1))


if __name__ == "__main__":
    asyncio.run(main())
