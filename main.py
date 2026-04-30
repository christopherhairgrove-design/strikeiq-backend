import os
import json
import re
from typing import Optional

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="StrikeIQ Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Anthropic client ─────────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

# ─── System prompt (identical to the one in services/claude.ts) ───────────────

SYSTEM_PROMPT = """You are an expert fishing guide and biologist with 30+ years of experience across North America. Provide specific, actionable fishing advice based on the given conditions.

WATER CLARITY & LURE COLOR:
- Crystal Clear: natural, realistic colors (silver, chrome, white, translucent). Finesse techniques, light line, subtle presentations.
- Slightly Stained: chartreuse, firetiger, white+chartreuse. More vibration in lures — fish rely on lateral line.
- Stained (1–2 ft visibility): bright chartreuse, orange, yellow, white. Add rattles. Spinnerbaits with large blades.
- Muddy (<1 ft): black, dark blue, dark purple (strong silhouette), or white (contrast). Loud rattles essential. Slow down.
- Very Muddy: black only. Painfully slow. Heavy vibration.

WATER TEMPERATURE & FISH METABOLISM:
- <40°F: Near-dormant. Tiny, ultra-slow finesse only. Deep stable water.
- 40–50°F: Very slow. Drop shot, shaky head, hair jigs. Wait 10+ sec between moves.
- 50–60°F: Pre-spawn activity (bass). Jerkbaits and swimbaits worked slowly.
- 60–70°F: Prime for most species. All techniques effective.
- 70–80°F: Peak feeding, especially dawn/dusk. Topwater highly productive.
- >80°F: Fish go deep or seek shade. Fish only early morning and evening.

CURRENT & STRUCTURE:
- Strong current: fish hold behind breaks (rocks, pilings, bends). Present upstream, wash into eddy.
- No current: target structure edges — weedlines, timber edges, depth changes.
- Flooded timber: suspend vertically. Crappie and bass stack in submerged trees.
- Heavy grass: frog, punch rig, swim jig. Weedless only.
- Rocky bottom: crawfish imitators (green pumpkin, brown). Carolina rig, football jig.
- Sandy bottom: swimbaits, blade baits, open water presentations.
- Dock structures: parallel casts, skip under docks, shade fishing.

SPECIES-SPECIFIC KNOWLEDGE:
- Largemouth Bass: cover-oriented. Power fishing in warm/stained, finesse in cold/clear. Beds in spring shallows.
- Smallmouth Bass: rocky, clear, cool water. Tubes, dropshots, jerkbaits. Fight current aggressively.
- Spotted Bass: schools in open water. Swimbait, drop shot, blade bait.
- Crappie: tight to vertical structure (brush piles, timber). Small jigs or live minnows. Dawn/dusk feeders.
- Bluegill: shallow vegetation, sand/gravel beds. Small jigs, worms, tiny poppers.
- Catfish: bottom feeders in current seams. Cut bait, punch bait, liver. Active after dark and during high water.
- Walleye: low-light species (dawn/dusk/night). Rocky points and reefs. Jigs + minnow, crawler harnesses. Cold-water specialist.
- Striped Bass: follows baitfish schools. Topwater when schooling. Chrome swimbaits, live bait.
- Brook Trout: pristine cold streams. Tiny dry flies, small spinners. Extremely wary.
- Brown Trout: most adaptable trout. Piscivorous when large. Streamers, Rapala lures. Dawn/dusk feeders.
- Rainbow Trout: active fighters, open water. Spoons, spinners, PowerBait.
- Pike: ambush in heavy vegetation. Large spinnerbaits, swimbaits, topwater. Most aggressive in cool water.
- Muskie: apex predator, giant presentations. Figure-8 at boatside mandatory. One strike per many casts.
- Redfish: tailing on flats at high tide. Gold spoons, soft plastics. Sight-fishing.
- Snook: structure ambush predator. Live bait, DOA shrimp, streamers. Dock lights at night.
- Flounder: bottom-dwelling ambush. Live mud minnows, Gulp, slow swim along bottom.

BAROMETRIC PRESSURE:
- Rising pressure: fish move shallower, more active. Great time to fish.
- Stable pressure: normal feeding patterns.
- Falling pressure: brief feeding flurry before front, then slow.
- Low stable: fish deep and slow.

Respond ONLY with a JSON object using this exact structure (no markdown, no extra text):
{
  "conditionsSummary": "2–3 sentence honest assessment of overall conditions and what to expect",
  "recommendedTactics": [
    { "technique": "technique name", "explanation": "why this works for these exact conditions" }
  ],
  "lureRecommendations": [
    { "lure": "specific lure type/model", "color": "exact colors", "why": "reason tied to conditions" }
  ],
  "whereToFish": "specific depth ranges, structure types, and positioning advice",
  "proTips": ["expert adjustment 1", "expert adjustment 2"]
}"""

# ─── Request / Response schemas ───────────────────────────────────────────────

class AdvisorRequest(BaseModel):
    water_clarity: str
    species: list[str]
    water_temp: Optional[float] = None
    water_level: str
    conditions: list[str]
    notes: str = ""
    time_of_day: str
    month: str
    spot_name: Optional[str] = None


class Tactic(BaseModel):
    technique: str
    explanation: str


class Lure(BaseModel):
    lure: str
    color: str
    why: str


class AdvisorResponse(BaseModel):
    conditionsSummary: str
    recommendedTactics: list[Tactic]
    lureRecommendations: list[Lure]
    whereToFish: str
    proTips: list[str]


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@app.post("/advisor", response_model=AdvisorResponse)
async def get_fishing_advice(req: AdvisorRequest):
    temp_str = "Unknown / skipped" if req.water_temp is None else f"{req.water_temp}°F"

    user_message = f"""Time: {req.time_of_day}, {req.month}
{f"Location: {req.spot_name}" if req.spot_name else ""}
Target Species: {", ".join(req.species) if req.species else "Not specified"}
Water Clarity: {req.water_clarity}
Water Temp: {temp_str}
Water Level: {req.water_level}
Water Conditions: {", ".join(req.conditions) if req.conditions else "None specified"}
Additional Notes: {req.notes or "None"}

Give me specific, actionable fishing advice for these exact conditions."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    text = message.content[0].text if message.content else ""
    if not text:
        raise HTTPException(status_code=502, detail="Empty response from Claude API")

    # Strip markdown fences if Claude wraps the JSON anyway
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        raise HTTPException(status_code=502, detail=f"Unexpected Claude response format: {text[:200]}")

    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse Claude JSON: {e}")

    return parsed


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
