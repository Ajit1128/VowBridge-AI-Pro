"""Server-only Qloo adapter. No credentials or Qloo response snapshots in the client/repository."""
from __future__ import annotations

import asyncio
import os
import time
import unicodedata
from typing import Any

import httpx

BASE_URL = "https://hackathon.api.qloo.com"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char)).strip()


class QlooError(Exception):
    pass


class QlooClient:
    def __init__(self, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.key = (api_key if api_key is not None else os.getenv("QLOO_API_KEY", "")).strip()
        self.transport = transport
        self.cache: dict[tuple, tuple[float, dict]] = {}

    @property
    def configured(self) -> bool:
        return bool(self.key)

    async def _get(self, path: str, params: dict[str, Any]) -> dict:
        if not self.key:
            raise QlooError("QLOO_API_KEY is not configured. Live recommendations are unavailable.")
        frozen = (path, tuple(sorted((k, str(v)) for k, v in params.items())))
        now = time.monotonic()
        cached = self.cache.get(frozen)
        if cached and now - cached[0] < 600:
            return cached[1]
        try:
            async with httpx.AsyncClient(timeout=16.0, transport=self.transport) as client:
                response = await client.get(
                    BASE_URL + path, params=params, headers={"X-Api-Key": self.key, "Accept": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise QlooError("Qloo returned an unexpected response structure")
                if len(self.cache) >= 250:
                    self.cache.clear()
                self.cache[frozen] = (now, data)
                return data
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            message = {401: "Qloo authentication rejected the server API key.",
                       403: "Qloo denied this query or entity category.",
                       429: "Qloo rate limit reached. Try again later."}.get(status, f"Qloo returned HTTP {status}.")
            raise QlooError(message) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise QlooError("Unable to reach Qloo or read its response. Check network/API availability.") from exc

    async def resolve_artist(self, name: str) -> dict | None:
        data = await self._get("/search", {"query": name, "types": "urn:entity:artist", "take": 7})
        results = data.get("results", [])
        if isinstance(results, dict):
            results = results.get("entities", [])
        if not isinstance(results, list):
            return None
        matches = [a for a in results if isinstance(a, dict) and a.get("entity_id") and
                   (not a.get("types") or "urn:entity:artist" in a.get("types", []))]
        # Exact normalized-name matching prevents silently resolving an unrelated musician.
        found = next((a for a in matches if norm(a.get("name", "")) == norm(name)), None)
        if not found:
            return None
        return {"id": str(found["entity_id"]), "name": str(found["name"]), "origin": "searched"}

    async def insights(self, ids: list[str], take: int = 20) -> list[dict]:
        if not ids:
            return []
        data = await self._get("/v2/insights", {
            "filter.type": "urn:entity:artist",
            "signal.interests.entities": ",".join(dict.fromkeys(ids)),
            "take": take,
            "feature.explainability": "true",
        })
        results = data.get("results", {})
        artists = results.get("entities", []) if isinstance(results, dict) else results
        if not isinstance(artists, list):
            return []
        cleaned = []
        for item in artists:
            if not isinstance(item, dict) or not item.get("entity_id") or not item.get("name"):
                continue
            query = item.get("query") or {}
            cleaned.append({
                "id": str(item["entity_id"]), "name": str(item["name"]),
                "origin": "insights", "affinity": query.get("affinity") if isinstance(query, dict) else None,
                "explainability": bool(isinstance(query, dict) and query.get("explainability")),
            })
        return cleaned


class FixtureQlooClient:
    """Completely synthetic offline UI preview. Never described as live Qloo evidence."""
    configured = False

    async def resolve_artist(self, name: str) -> dict:
        clean = name.strip()
        return {"id": "fixture:" + norm(clean).replace(" ", "-"), "name": clean, "origin": "fixture"}

    async def insights(self, ids: list[str], take: int = 20) -> list[dict]:
        # Deterministic, explicitly invented fixture artists, not copied Qloo data.
        if len(ids) >= 3:
            names = ["Demo Fusion Ensemble", "Demo Cross-Culture Collective", "Demo Rhythm Project"]
        elif any("arijit" in x or "diljit" in x for x in ids):
            names = ["Demo Fusion Ensemble", "Demo Raag Collective", "Demo Cross-Culture Collective", "Demo South Asian Quartet"]
        else:
            names = ["Demo Fusion Ensemble", "Demo Latin Quartet", "Demo Cross-Culture Collective", "Demo Afro-Latin Ensemble"]
        return [{"id": "fixture:" + norm(name).replace(" ", "-"), "name": name, "origin": "fixture",
                 "affinity": None, "explainability": False} for name in names[:take]]
