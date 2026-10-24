"""
Records the demo footage with Playwright while a real (seeded) match plays.

Writes build/match.webm plus build/markers.json with the time, in seconds from the
start of the recording, of every moment the edit needs.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).parent / "build"
VIEWPORT = {"width": 2048, "height": 1152}
VIDEO = {"width": 1920, "height": 1080}


class Recorder:
    def __init__(self, page, t0):
        self.page, self.t0, self.markers = page, t0, {}

    def now(self):
        return round(time.monotonic() - self.t0, 2)

    def mark(self, name):
        self.markers[name] = self.now()
        print(f"{self.markers[name]:7.2f}s  {name}")

    def js(self, code, arg=None):
        return self.page.evaluate(code, arg)

    def wait_until(self, code, timeout=90, poll=0.1):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.js(code):
                return True
            time.sleep(poll)
        raise TimeoutError(code)

    def scroll_to(self, selector, offset=0):
        self.js("""([sel, off]) => {
            const el = document.querySelector(sel);
            const y = el.getBoundingClientRect().top + window.scrollY - off;
            window.scrollTo({top: Math.max(0, y), behavior: 'smooth'});
        }""", [selector, offset])

    def set_select(self, sel_id, value):
        self.js("""([id, v]) => { const el = document.getElementById(id); el.value = v;
                   el.dispatchEvent(new Event('change')); }""", [sel_id, value])


def record_match():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, record_video_dir=str(OUT / "raw"),
                                      record_video_size=VIDEO, device_scale_factor=1)
        page = context.new_page()
        t0 = time.monotonic()
        r = Recorder(page, t0)

        page.goto(f"{BASE}/?demo=1")
        page.wait_for_function("window.omniPitch && document.fonts.status === 'loaded'")
        # English, analyst, spotlight on Drake, 2x pace, fresh match
        r.set_select("player-select", "Julian Drake")
        r.js("document.querySelector('#speed-toggle [data-speed=\"2\"]').click()")
        r.js("omniPitch.resetSimulation()")
        time.sleep(2.0)

        # Scene 2: kick-off in English
        r.mark("s2_start")
        r.js("document.getElementById('btn-stream-toggle').click()")
        time.sleep(7)
        r.scroll_to(".main-layout", 90)
        time.sleep(7)

        # Scene 3: Italian, fan, Avalon City
        r.mark("s3_start")
        r.scroll_to("#scoreboard", 70)
        time.sleep(0.8)
        r.set_select("lang-select", "it")
        time.sleep(0.5)
        r.js("document.getElementById('btn-fan').click()")
        time.sleep(0.5)
        r.set_select("club-select", "avalon_city")
        time.sleep(1.5)
        r.scroll_to(".telemetry-card", 420)
        # Wait for the next goal call in Italian and remember its text
        r.js("""() => {
            window.__goals = [];
            const orig = omniPitch.appendCommentary.bind(omniPitch);
            omniPitch.appendCommentary = (lines) => {
                lines.forEach((l) => {
                    if (l.speaker === 'lead' && l.intensity === 3) window.__goals.push({text: l.text, t: performance.now()});
                });
                orig(lines);
            };
        }""")
        r.wait_until("window.__goals.length > 0 && window.__goals[0].text.includes('Thorne') || window.__goals.length > 1", timeout=60)
        r.mark("goal_it")
        goal_line = r.js("window.__goals[window.__goals.length - 1].text")
        time.sleep(4)

        # Scene 4: stoppage time board, half-time pause and report
        r.wait_until("!document.getElementById('added-badge').classList.contains('hidden')", timeout=60)
        r.scroll_to("#scoreboard", 70)
        r.mark("added_time")
        r.wait_until("!document.getElementById('recap-modal').classList.contains('hidden')", timeout=60)
        r.mark("ht_report")
        time.sleep(6)

        # Scene 5: back to English analyst, verifier at work
        r.js("omniPitch.closeRecap()")
        r.set_select("club-select", "")
        r.set_select("lang-select", "en")
        r.js("document.getElementById('btn-analyst').click()")
        time.sleep(0.6)
        r.mark("s5_start")
        r.js("document.getElementById('btn-stream-toggle').click()")
        time.sleep(4)
        r.js("document.getElementById('btn-toggle-json').click()")
        r.scroll_to("#broadcast-card", 80)
        time.sleep(4)
        r.js("omniPitch.activateTab('tab-foundry')")
        r.scroll_to("#matchcenter-section", 70)
        time.sleep(6)

        # Scene 6: match centre
        r.mark("s6_start")
        r.js("omniPitch.activateTab('tab-momentum')")
        time.sleep(3.5)
        r.js("omniPitch.activateTab('tab-shotmap')")
        time.sleep(3)
        r.js("omniPitch.activateTab('tab-timeline')")
        time.sleep(3)

        # Scene 8: full-time report
        r.wait_until("omniPitch.fullTime && !document.getElementById('recap-modal').classList.contains('hidden')", timeout=90)
        r.mark("ft_report")
        time.sleep(5)
        r.mark("end")

        last_goal = r.js("(omniPitch.matchCenterData.timeline || []).filter(t => t.type === 'goal').pop()")
        context.close()
        browser.close()

        raw = sorted((OUT / "raw").glob("*.webm"), key=lambda f: f.stat().st_mtime)[-1]
        raw.replace(OUT / "match.webm")
        (OUT / "markers.json").write_text(json.dumps(
            {"markers": r.markers, "goal_line_it": goal_line, "last_goal": last_goal}, indent=2, ensure_ascii=False), encoding="utf-8")
        print("goal line:", goal_line)


if __name__ == "__main__":
    record_match()
