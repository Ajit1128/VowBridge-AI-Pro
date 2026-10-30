# VowBridge AI Pro — Devpost description (draft)

## Inspiration
Multicultural weddings ask professional DJs to bring two families onto one dance floor. Their preferences can differ widely, and conventional AI tends to recommend generic or invented "fusion" ideas with little justification. We built an evidence-led cultural planning assistant for this specific job.

## What it does
VowBridge AI Pro takes favorite artists from each family, uses Qloo to look up the artist IDs, gathers three independent taste recommendation sets (side A, side B, and joint), and builds a 10-block wedding music program. The user can ban an artist or change the event duration, then regenerate and export a DJ-ready planning CSV.

## Why Qloo is essential
Without Qloo, the system can at most alternate the favorite artists already supplied. With Qloo, it discovers related artists and verifies whether a candidate appears independently in the recommendation lists for both families. The interface exposes those artist names and identifiers, distinguishes real Qloo responses from synthetic preview fixtures, and does not claim that affinities guarantee personal enjoyment.

## How the agent works
A deterministic tool-using agent performs a multi-step loop: resolve artists → request two separate and one combined Insights queries → compare evidence → construct four candidate runs of show → critique and select a verified plan → independently verify time, exclusions, provenance and group representation → produce results or reject the schedule. When exclusions change, the entire proposal is regenerated and rechecked.

## Built with
Python, FastAPI, Qloo Search API, Qloo Insights API, JavaScript, HTML, CSS, pytest; deployment with Docker and Render.

## Challenges
Maintaining meaningful Qloo provenance, avoiding unsupported cultural "fusion" guesses, enforcing strict artist identity resolution, and making the application work as a standalone public demo.

## What's next
Consent-based guest feedback, DJ-provided song inventory, rights-aware track scheduling, service-provider partnerships and experiments that measure outcomes rather than merely asserting them.

## Safety / limitations
This is an **artist-level** event plan, not an exact playlist. Musical transitions, licensing, individual guest enjoyment and live artist availability are out of scope. A DJ should review the proposal. Synthetic preview results are never described as real Qloo data.
