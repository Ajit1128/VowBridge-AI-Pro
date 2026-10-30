"""Transparent multi-step planner with a deterministic verifier and repair loop.

Qloo supplies artist identity and interest-based candidate sets. It does not supply
song durations, guaranteed personal enjoyment, event availability or licensing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.qloo import norm


class PlanError(Exception):
    pass


def dedupe(artists: list[dict], excluded: set[str] | None = None) -> list[dict]:
    excluded = excluded or set()
    seen: set[str] = set()
    out: list[dict] = []
    for a in artists:
        if a['id'] in seen or norm(a['name']) in excluded:
            continue
        out.append(a)
        seen.add(a['id'])
    return out


def distribute(total_minutes: int, vibe: str = "balanced") -> list[int]:
    """Allocate ten positive, five-minute-aligned programming slots exactly."""
    units = total_minutes // 5
    weights = {
        "balanced": [0.10, 0.10, 0.12, 0.13, 0.10, 0.10, 0.09, 0.08, 0.09, 0.09],
        "elegant": [0.13, 0.12, 0.15, 0.15, 0.10, 0.10, 0.07, 0.06, 0.06, 0.06],
        "high-energy": [0.08, 0.08, 0.09, 0.09, 0.09, 0.09, 0.12, 0.12, 0.12, 0.12],
    }.get(vibe, [0.10, 0.10, 0.12, 0.13, 0.10, 0.10, 0.09, 0.08, 0.09, 0.09])
    allocated = [1] * len(weights)
    remaining = units - len(weights)
    raw = [w * remaining for w in weights]
    floors = [int(x) for x in raw]
    for index, value in enumerate(floors):
        allocated[index] += value
    diff = units - sum(allocated)
    priority = sorted(range(len(weights)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in priority[:diff]:
        allocated[i] += 1
    return [u * 5 for u in allocated]


STAGES = ["Welcome", "Welcome", "Dinner", "Dinner", "Build-up", "Build-up",
          "Dance floor", "Dance floor", "Dance floor", "Dance floor"]


def verify_slots(slots: list[dict], minutes: int, banned: set[str], evidence_ids: set[str]) -> dict:
    reasons = []
    if len(slots) != 10:
        reasons.append("Expected exactly 10 programming blocks")
    if sum(s['minutes'] for s in slots) != minutes:
        reasons.append("Time allocation does not match the event duration")
    if any(s['minutes'] <= 0 or s['minutes'] % 5 for s in slots):
        reasons.append("Invalid block duration")
    if any(norm(s['artist']) in banned for s in slots):
        reasons.append("A blocked artist is still included")
    if any(s['entity_id'] not in evidence_ids for s in slots):
        reasons.append("An artist is not grounded in the query evidence")
    a = sum(s['minutes'] * (0.5 if s['side'] == 'bridge' else 1 if s['side'] == 'a' else 0) for s in slots)
    b = sum(s['minutes'] * (0.5 if s['side'] == 'bridge' else 1 if s['side'] == 'b' else 0) for s in slots)
    if a < minutes * .35 or b < minutes * .35:
        reasons.append("A side received less than 35% of scheduled representation")
    return {"passed": not reasons, "checks": [
        {"name": "Exact time allocation", "passed": sum(s['minutes'] for s in slots) == minutes},
        {"name": "Blocked artists excluded", "passed": not any(norm(s['artist']) in banned for s in slots)},
        {"name": "Qloo-grounded artist identities", "passed": all(s['entity_id'] in evidence_ids for s in slots)},
        {"name": "At least 35% representation per side", "passed": a >= minutes*.35 and b >= minutes*.35},
    ], "warnings": reasons, "a_minutes_equivalent": round(a), "b_minutes_equivalent": round(b)}


async def build_plan(client, a_names: list[str], b_names: list[str], duration: int,
                     blocked: list[str], vibe: str = "balanced", preview: bool = False) -> dict:
    banned = {norm(x) for x in blocked if x.strip()}
    activity = [{"action": "Receive constraints", "detail": "Validate inputs, length, and artist exclusions."}]

    async def resolve(names: list[str], side: str) -> tuple[list[dict], list[str]]:
        selected: list[dict] = []
        unknown = []
        for name in names:
            artist = await client.resolve_artist(name)
            if artist is None:
                unknown.append(name)
            elif norm(artist['name']) not in banned:
                selected.append(artist)
        activity.append({"action": f"Resolve side {side} artists", "detail": f"{len(selected)} resolved; {len(unknown)} unknown."})
        return dedupe(selected), unknown

    side_a, unknown_a = await resolve(a_names, "A")
    side_b, unknown_b = await resolve(b_names, "B")
    if not side_a or not side_b:
        raise PlanError("Each side needs at least one recognized, non-blocked artist. Try another favorite or remove an exclusion.")
    a_recs = dedupe(await client.insights([a['id'] for a in side_a], take=24), banned)
    b_recs = dedupe(await client.insights([b['id'] for b in side_b], take=24), banned)
    combined = dedupe(await client.insights([a['id'] for a in side_a + side_b], take=24), banned)
    activity.append({"action": "Query Qloo cultural graph", "detail": "Retrieved separate A/B recommendation lists and a joint recommendation list."})
    activity.append({"action": "Compare the audiences", "detail": "Shared candidates require appearance in both sides' Qloo candidate lists."})
    # A true 'bridge' appears independently in each side's candidate list.
    group_a_ids = {x['id'] for x in side_a + a_recs}
    group_b_ids = {x['id'] for x in side_b + b_recs}
    bridge = dedupe([x for x in combined + a_recs + b_recs if x['id'] in group_a_ids & group_b_ids], banned)
    # Side-specific slots must be supported by that side's actual signal, not just joint results.
    pool_a = dedupe(side_a + a_recs, banned)
    pool_b = dedupe(side_b + b_recs, banned)
    if not pool_a or not pool_b:
        raise PlanError("Qloo has insufficient artist data to create a two-sided plan.")
    # 'Bridge' slots are replaced by alternating family-specific slots if evidence is weak.
    roles = ["a", "b", "a", "b", "bridge", "a", "b", "bridge", "a", "b"]
    if not bridge:
        roles = ["a", "b", "a", "b", "a", "b", "a", "b", "a", "b"]
    lengths = distribute(duration, vibe)
    sources = {"a": pool_a, "b": pool_b, "bridge": bridge}
    evidence_ids = {x['id'] for x in side_a + side_b + a_recs + b_recs + combined}
    input_ids = {x['id'] for x in side_a + side_b}
    candidates = []
    # The planner creates alternatives, executes the same independent checks on
    # each, and selects the most diverse VERIFIED proposal. No opaque LLM score.
    for variant in range(4):
        cursors = {"a": variant, "b": variant, "bridge": variant}
        draft = []
        timestamp = 0
        for index, (role, mins) in enumerate(zip(roles, lengths)):
            choices = sources[role]
            artist = choices[cursors[role] % len(choices)]
            cursors[role] += 1
            draft.append({"number": index+1, "stage": STAGES[index], "start_minute": timestamp,
                          "minutes": mins, "side": role, "artist": artist['name'],
                          "entity_id": artist['id'], "source": "fixture" if preview else "Qloo",
                          "reason": ("Suggested independently for both sides by the taste engine" if role == "bridge" else
                                     "Grounded in side A's artist tastes" if role == "a" else "Grounded in side B's artist tastes"),
                          "is_new_discovery": artist['id'] not in input_ids})
            timestamp += mins
        check = verify_slots(draft, duration, banned, evidence_ids)
        chosen_ids = {x['entity_id'] for x in draft}
        # Diversity, new evidence-backed discoveries, and inclusion of favorites.
        quality = (len(chosen_ids)*2 + len(chosen_ids - input_ids)*2 +
                   len(chosen_ids & input_ids)*3)
        candidates.append((check['passed'], quality, draft, check))
    activity.append({"action": "Critique four candidate programs", "detail": "Check each schedule independently; rank valid schedules by artist diversity, grounded discoveries, and favorite coverage."})
    valid = [candidate for candidate in candidates if candidate[0]]
    if not valid:
        warnings = candidates[0][3]['warnings']
        activity.append({"action": "Reject unverified plan", "detail": "; ".join(warnings)})
        raise PlanError("No generated schedule passed independent validation: " + "; ".join(warnings))
    _, quality, slots, audit = max(valid, key=lambda c: c[1])
    activity.append({"action": "Select best verified proposal", "detail": f"Selected a valid schedule from {len(valid)} passing variants; diversity score {quality} is an internal planning heuristic."})
    activity.append({"action": "Publish verified proposal", "detail": "Generated artist-level slots only; song availability and rights remain DJ responsibilities."})
    return {
        "status": "verified_proposal", "mode": "synthetic-preview" if preview else "live-qloo",
        "duration": duration, "vibe": vibe, "audiences": {"a": [a['name'] for a in side_a], "b": [b['name'] for b in side_b]},
        "unresolved": {"a": unknown_a, "b": unknown_b},
        "timeline": slots, "verification": audit, "agent_trace": activity,
        "taste_evidence": {
            "a": a_recs[:8], "b": b_recs[:8], "shared": bridge[:8], "combined": combined[:10],
            "qloo_calls_expected": 3 + len(a_names) + len(b_names),
            "basis": "Independent Qloo Insights for side A, side B, and their combined inputs" if not preview else "Invented fixtures for UI demonstration only",
        },
        "difference_from_no_qloo": {
            "new_recommendations_in_plan": len({s['entity_id'] for s in slots if s['is_new_discovery']}),
            "independently_shared_candidates": len(bridge),
            "baseline": "Seed-only alternation cannot discover new artists; this is a descriptive contrast, not an A/B study."
        },
        "disclaimer": "This is an artist-level programming proposal, not a song playlist. Qloo does not validate musical transitions, music licensing, DJ inventory, or guest satisfaction. Review with the DJ and couple.",
    }
