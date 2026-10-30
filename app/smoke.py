"""Verify the real Qloo Hackathon API using the local .env, without revealing the key."""
import asyncio
from dotenv import load_dotenv

from app.qloo import QlooClient, QlooError


async def main():
    load_dotenv()
    client = QlooClient()
    if not client.configured:
        print("ERROR: Add your key as QLOO_API_KEY=... to .env first.")
        return 1
    print("Checking live Qloo artist search and Insights (private key is never printed)...")
    try:
        first = await client.resolve_artist("Bad Bunny")
        second = await client.resolve_artist("Shakira")
        for seed in (first, second):
            if seed is None:
                print("Artist search returned no exact match. Check Qloo data or try a different artist.")
                return 1
            print("Artist recognized:", seed["name"], seed["id"])
        results = await client.insights([first["id"], second["id"]], take=5)
        if not results:
            print("Qloo responded, but no artist recommendations were returned.")
            return 1
        print("LIVE QLOO INSIGHTS: SUCCESS", len(results), "artists")
        for item in results:
            print(" -", item["name"], item["id"])
        return 0
    except QlooError as exc:
        print("Qloo could not complete the check:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
