import time
import json
import os
import re
import requests

DELAY_SECONDS = 1.5


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}







def _title_slug(title: str) -> str:
    slug = title.lower()
    for ch in [":", "'", ".", ",", "!", "?", "&"]:
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def scrape_metacritic(title: str, platform: str) -> dict | None:
    

    time.sleep(DELAY_SECONDS)

    # Usar RAWG que no tiene problemas SSL y tiene metacritic score
    RAWG_API_KEY = "c7bc9a9466334f33817da7de7aaad83e"
    RAWG_URL     = "https://api.rawg.io/api/games"

    try:
        r = requests.get(
            RAWG_URL,
            params={"key": RAWG_API_KEY, "search": title, "page_size": 1},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None

    if r.status_code != 200:
        return None

    results = r.json().get("results", [])
    if not results:
        return None

    game_id = results[0].get("id")
    slug    = results[0].get("slug", "")

    time.sleep(DELAY_SECONDS)

    try:
        r2 = requests.get(
            f"{RAWG_URL}/{game_id}",
            params={"key": RAWG_API_KEY},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None

    if r2.status_code != 200:
        return None

    detail     = r2.json()
    metascore  = detail.get("metacritic")
    # RAWG no tiene user score — usamos ratings como proxy (escala 1-5 → *20 para llevar a 100)
    rating     = detail.get("rating")
    user_score = round(float(rating) * 20, 1) if rating else None

    if not metascore:
        return None

    result = {
        "metascore":  int(metascore),
        "user_score": user_score,
        "platform":   platform,
        "url": f"https://www.metacritic.com/game/{_title_slug(title)}/",
    }

 
    return result