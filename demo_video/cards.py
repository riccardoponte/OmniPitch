"""
Builds and records the non-dashboard shots:
- title card, closing card (static HTML in the app's visual language)
- MCP scene: a real MCP session against the running app, rendered as a terminal
"""
import asyncio
import html
import json
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "build"
VIEWPORT = {"width": 1920, "height": 1080}
FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Barlow:wght@400;500;600"
         "&family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@1,6..72,400&display=swap")

BASE_CSS = """
:root { --bg:#0b0c0e; --text:#ecebe6; --t2:#a3a39d; --t3:#6c6c67; --accent:#d2ff3c; --home:#2fa6ff; --away:#ff5140; }
* { margin:0; box-sizing:border-box; }
body { width:1920px; height:1080px; background: radial-gradient(1400px 700px at 50% -200px, rgba(236,235,230,.07), transparent 70%), var(--bg);
       color:var(--text); font-family:'Barlow',sans-serif; overflow:hidden; }
.bar { position:absolute; top:0; left:0; right:0; height:6px; background:linear-gradient(90deg,var(--home) 0 50%,var(--away) 50% 100%); }
@keyframes rise { from { opacity:0; transform:translateY(24px) } to { opacity:1; transform:none } }
.rise { animation: rise .9s cubic-bezier(.2,.7,.2,1) both; }
"""


def title_html():
    return f"""<!doctype html><html><head><meta charset="utf-8"><link href="{FONTS}" rel="stylesheet"><style>{BASE_CSS}
.wrap {{ position:absolute; inset:0; display:flex; flex-direction:column; justify-content:center; padding:0 180px; }}
.eyebrow {{ font-family:'IBM Plex Mono'; font-size:22px; letter-spacing:.18em; color:var(--t3); text-transform:uppercase; }}
h1 {{ font-family:'Barlow Condensed'; font-weight:800; font-size:220px; letter-spacing:.04em; line-height:.9; margin:18px 0 26px; }}
h1 span {{ font-weight:600; }}
p {{ font-family:'Newsreader'; font-style:italic; font-size:52px; color:var(--t2); max-width:1300px; line-height:1.25; }}
.dot {{ display:inline-block; width:22px; height:22px; background:var(--accent); border-radius:50%; margin-left:18px; vertical-align:middle; }}
</style></head><body><div class="bar"></div><div class="wrap">
<div class="eyebrow rise">Inside the Game · Developer Hackathon</div>
<h1 class="rise" style="animation-delay:.25s"><span>OMNI</span>PITCH<i class="dot"></i></h1>
<p class="rise" style="animation-delay:.6s">A live football broadcast, written by AI agents — and fact-checked before it reaches air.</p>
</div></body></html>"""


def closing_html():
    techs = ["Microsoft Foundry", "Model Context Protocol", "GitHub Copilot", "Azure Container Apps",
             "Azure Event Hubs", "Microsoft Fabric", "Teams Adaptive Cards"]
    chips = "".join(f'<span class="chip rise" style="animation-delay:{.35 + i * .08:.2f}s">{t}</span>' for i, t in enumerate(techs))
    return f"""<!doctype html><html><head><meta charset="utf-8"><link href="{FONTS}" rel="stylesheet"><style>{BASE_CSS}
.wrap {{ position:absolute; inset:0; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }}
h1 {{ font-family:'Barlow Condensed'; font-weight:800; font-size:150px; letter-spacing:.04em; }}
h1 span {{ font-weight:600; }}
p {{ font-family:'Newsreader'; font-style:italic; font-size:56px; color:var(--t2); margin:6px 0 54px; }}
.chips {{ display:flex; flex-wrap:wrap; justify-content:center; gap:14px; max-width:1400px; }}
.chip {{ font-family:'IBM Plex Mono'; font-size:24px; padding:10px 18px; border:1px solid rgba(236,235,230,.2); border-radius:4px; color:var(--text); }}
.url {{ margin-top:60px; font-family:'IBM Plex Mono'; font-size:26px; color:var(--accent); }}
.note {{ margin-top:14px; font-family:'IBM Plex Mono'; font-size:18px; color:var(--t3); }}
</style></head><body><div class="bar"></div><div class="wrap">
<h1 class="rise"><span>OMNI</span>PITCH</h1>
<p class="rise" style="animation-delay:.15s">Every match, made for every fan.</p>
<div class="chips">{chips}</div>
<div class="url rise" style="animation-delay:1.1s">github.com/riccardoponte/OmniPitch</div>
<div class="note rise" style="animation-delay:1.3s">All clubs, players and competitions are fictional · synthetic match data</div>
</div></body></html>"""


async def mcp_transcript(event_id: str):
    async with streamable_http_client("http://127.0.0.1:8000/mcp/") as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            # The match is seeded, so replaying it reproduces the recorded events exactly
            state = json.loads((await session.call_tool("get_match_state", {})).content[0].text)
            if state["status"]["phase"] != "full_time":
                while True:
                    step = json.loads((await session.call_tool("advance_match", {})).content[0].text)
                    if step.get("full_time"):
                        break
            res = await session.call_tool("explain_moment", {"event_id": event_id, "persona": "analyst", "language": "en"})
            data = json.loads(res.content[0].text)
            return tools, data


def mcp_html(tools, data, event_id):
    ev = data["event"]
    ver = data["verification"]
    rows = [
        ("prompt", "Why did the last goal matter?"),
        ("cmd", f"tools/call  explain_moment  {{\"event_id\": \"{event_id}\", \"persona\": \"analyst\"}}"),
        ("key", f"event        {ev['event_id']} · {ev['match_minute_label']} · {ev['event_type']} · {ev['player']['name']}"),
        ("key", f"headline     {data['headline']}"),
        ("val", f"explanation  {data['explanation']}"),
        ("key", f"evidence     {', '.join(data['evidence_event_ids'])}"),
        ("ok", f"verifier     grounded={str(ver['is_grounded']).lower()} · {ver['claims_checked']} claims checked · {len(ver['rejected_claims'])} rejected"),
    ]
    lines = []
    for i, (kind, text) in enumerate(rows):
        delay = 0.9 + i * 0.75
        lines.append(f'<div class="ln {kind}" style="animation-delay:{delay:.2f}s">{html.escape(text)}</div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><link href="{FONTS}" rel="stylesheet"><style>{BASE_CSS}
.term {{ position:absolute; left:140px; right:140px; top:120px; bottom:120px; background:#111215; border:1px solid rgba(236,235,230,.12);
        border-radius:10px; overflow:hidden; box-shadow:0 40px 80px -30px #000; }}
.head {{ display:flex; gap:14px; align-items:center; padding:18px 26px; border-bottom:1px solid rgba(236,235,230,.08);
        font-family:'IBM Plex Mono'; font-size:20px; color:var(--t2); }}
.head b {{ color:var(--accent); font-weight:600; }}
.tools {{ padding:18px 26px 6px; font-family:'IBM Plex Mono'; font-size:19px; color:var(--t3); }}
.tools span {{ color:var(--t2); }}
.body {{ padding:16px 26px; font-family:'IBM Plex Mono'; font-size:25px; line-height:1.55; }}
.ln {{ opacity:0; animation: rise .45s ease both; white-space:pre-wrap; margin-bottom:10px; }}
.prompt {{ font-family:'Newsreader'; font-style:italic; font-size:40px; color:var(--text); margin-bottom:20px; }}
.prompt::before {{ content:'› '; color:var(--accent); font-style:normal; }}
.cmd {{ color:var(--accent); }}
.key {{ color:var(--text); }}
.val {{ color:var(--t2); }}
.ok {{ color:#3fd28b; }}
</style></head><body><div class="bar"></div><div class="term">
<div class="head"><b>MCP</b> streamable-http · localhost:8000/mcp/ · server: omnipitch</div>
<div class="tools">tools/list → <span>{html.escape(' · '.join(tools))}</span></div>
<div class="body">{''.join(lines)}</div></div></body></html>"""


def record_page(browser, name, content, seconds):
    path = OUT / f"{name}.html"
    path.write_text(content, encoding="utf-8")
    ctx = browser.new_context(viewport=VIEWPORT, record_video_dir=str(OUT / "raw_cards"), record_video_size=VIEWPORT)
    page = ctx.new_page()
    page.goto(path.as_uri())
    page.wait_for_function("document.fonts.status === 'loaded'")
    time.sleep(seconds)
    video = page.video
    ctx.close()
    Path(video.path()).replace(OUT / f"{name}.webm")


def main():
    markers = json.loads((OUT / "markers.json").read_text(encoding="utf-8"))
    event_id = markers["last_goal"]["event_id"]
    tools, data = asyncio.run(mcp_transcript(event_id))
    (OUT / "mcp_result.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        record_page(browser, "title", title_html(), 11.5)
        record_page(browser, "mcp", mcp_html(tools, data, event_id), 10.5)
        record_page(browser, "closing", closing_html(), 9)
        browser.close()
    print("headline:", data["headline"])
    print("explanation:", data["explanation"])


if __name__ == "__main__":
    main()
