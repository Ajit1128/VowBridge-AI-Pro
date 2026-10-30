# VowBridge AI Pro 💍 ✦

**Two cultures. One unforgettable dance floor.**

An agentic cultural wedding-programming studio for DJs and planners of multicultural receptions. It consults the **Qloo Taste Graph API** to understand each family's artist preferences independently, explores cross-audience overlap, creates a ten-block artist-level reception program, and independently verifies duration, artist provenance, exclusions, and each family's time representation.

> **Important distinction:** The product proposes *artist programming blocks*, not a song-accurate playlist. Qloo does not prove that guests will enjoy a selection, that a DJ possesses particular songs, or that music licenses/artist appearances are secured. All displayed affinities are evidence from Qloo only in **Live Qloo** mode. **Synthetic preview** is explicitly artificial.

## The problem & niche

Professional DJs and wedding planners serving **multicultural couples** must reconcile two sets of tastes while keeping a concrete run of show. Generic LLM recommendations are often ungrounded. The tool uses Qloo to discover relevant artists and verifies concrete constraints without making unsupported satisfaction promises.

## Features

- **Independent taste searches:** up to four favorite artists for each family are looked up through `GET /search`, and only exact normalized artist-name matches are accepted.
- **Three cultural intelligence calls:** Qloo Insights for side A, side B, and both groups combined (`GET /v2/insights`, `filter.type=urn:entity:artist`, `feature.explainability=true`).
- **Evidence-driven bridge:** a "shared" artist must appear independently in both sides' taste candidate sets. If no shared artist is found, no shared recommendation is fabricated.
- **Agentic workflow:** resolve → retrieve separate/joint recommendations → compare → construct four alternative programs → critique each against an independent verifier → choose the most diverse valid proposal → release. A change to the do-not-play list triggers replanning and reverification.
- **Deterministic verifier:** exactly 10 slots with durations totaling the requested event length, no banned artists, artist IDs grounded in Qloo results, and at least 35% representation for each side (shared time counted half for each).
- **Transparent comparison:** explicitly states what Qloo adds over seed-only alternation, without claiming a scientific performance improvement.
- **Export:** JSON evidence bundle and CSV DJ schedule.
- **Private API keys:** credentials stay exclusively on the FastAPI server.
- **Rate limiting:** basic per-process throttling for public demos and ten-minute in-memory Qloo response cache.

## Quick start · Windows PowerShell

```powershell
cd "$HOME\Downloads\VowBridge-AI-Pro"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

In your local **`.env`** enter:

```ini
QLOO_API_KEY=PASTE_YOUR_PRIVATE_HACKATHON_KEY_HERE
```

Use the hackathon endpoint only: `https://hackathon.api.qloo.com`. Do **not** put the key in a browser or GitHub. Then launch:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Before opening the UI, verify artist support with the **real** API (this makes live requests and prints only public artist data):

```powershell
.\.venv\Scripts\python.exe -m app.smoke
```

If the test fails, do not claim the project is Qloo-integrated yet; review the error or consult Qloo #api-help.

Visit **http://127.0.0.1:8000**. Choose **Live Qloo** for actual API calls. The synthetic preview works without a key and is clearly marked.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use fully fictional fixtures, do **not** need your Qloo key, and must never be reported as end-to-end live Qloo proof. Before submission, verify **live artist queries** with the actual key and the final public deployment.

## Public deployment (Render)

1. Publish the repository on GitHub as **public** and confirm that GitHub detects the MIT `LICENSE` file.
2. On Render, select **New → Blueprint** and connect the repository using the included `render.yaml`; or create a free Web Service with Docker runtime.
3. Enter **QLOO_API_KEY** in the service's **private environment variables**, never in a committed file.
4. Wait for the build to become live and verify `https://YOUR-HOST/api/health` shows `"live_qloo_available": true`.
5. Load the public website and generate a real Qloo plan for both groups. Confirm the UI says **LIVE QLOO** and the recommendations contain actual artist IDs.
6. Keep the public demo accessible for the entire Qloo judging period. Free hosting may sleep after inactivity.

**Security notice:** This is a hackathon prototype. It has best-effort in-memory per-IP throttling, which does not constitute production API cost protection or multi-instance abuse prevention. Keep an eye on Qloo quota. Do not publish other participants' personal information. No Qloo API payloads are checked into this repository.

## Architecture

```text
Browser (HTML/CSS/JS) --POST /api/plan--> FastAPI backend
     ↳ Qloo search /search [resolve actual artist IDs]
     ↳ Qloo insights side A, side B, together
     ↳ Shared-affinity candidate intersection
     ↳ Ten-block deterministic run-of-show planner
     ↳ Independent verifier & agent trace
     ↳ JSON response to browser → charts, evidence, exports
```

## API request

`POST /api/plan`

```json
{
  "group_a": ["Arijit Singh", "Diljit Dosanjh"],
  "group_b": ["Bad Bunny", "Karol G"],
  "duration": 180,
  "vibe": "balanced",
  "banned": [],
  "preview": false
}
```

`preview: false` requires a real key on the server. `preview: true` generates clearly labeled, fabricated fixtures for visual testing only.

## Hackathon submission checklist

- [ ] Qloo live mode tested with artist entities from both input groups
- [ ] Site deployed at a **public** URL (localhost is insufficient)
- [ ] README instructions and source code pushed to public GitHub
- [ ] MIT license visible in repository About section
- [ ] Written project submission and explanation of why Qloo is indispensable
- [ ] Public app reachable through the judging period
- [ ] No secret keys in commits, network response payloads, or screenshots

Official rules: https://qloo.devpost.com/rules
Qloo developer guide: https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide

## Intellectual property & limitations

We do not reproduce or play copyrighted music, display lyrics, or claim music-performance licensing. Qloo entities do not guarantee the preferences of actual guests, cultural representativeness of a population, artist availability, or appropriateness of any particular song. The couple and DJ should approve the plan.

## License

MIT — see [LICENSE](LICENSE).
