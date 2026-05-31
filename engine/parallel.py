"""
engine/parallel.py
------------------
Motor paralelo con 3 niveles de concurrencia:

  Nivel 1 — Juegos en paralelo      → ProcessPoolExecutor (max_workers=4)
  Nivel 2 — Tiendas en paralelo     → ThreadPoolExecutor  (max_workers=3)
  Nivel 3 — Plataformas Metacritic  → ThreadPoolExecutor  (max_workers ilimitado*)

*Por defecto usa tantos hilos como plataformas tenga el juego.

Para cambiar la cantidad de workers, edita las constantes al inicio del archivo.
"""

import time
import sys
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.metacritic    import scrape_metacritic
from scrapers.howlongtobeat import scrape_hltb
from scrapers.steam         import scrape_steam
from scrapers.amazon        import scrape_amazon
from scrapers.psstore       import scrape_psstore

# ── Ajusta estos valores para controlar el paralelismo ──────────────────────
GAME_WORKERS     = 4   # Cuántos juegos procesar en paralelo (Nivel 1)
STORE_WORKERS    = 3   # Cuántas tiendas consultar en paralelo por juego (Nivel 2)
# Nivel 3 usa tantos hilos como plataformas tenga el juego (normalmente 2-5)
# ─────────────────────────────────────────────────────────────────────────────


def _scrape_prices_parallel(title: str, reference_price: float) -> list:
    """
    NIVEL 2: llama a las 3 tiendas en paralelo usando hilos.
    Retorna lista de dicts de precio (solo los que no sean None).
    """
    prices = []

    # Mapeamos cada scraper con sus argumentos
    tasks = {
        "steam":   (scrape_steam,    (title, reference_price)),
        "amazon":  (scrape_amazon,   (title,)),
        "psstore": (scrape_psstore,  (title,)),
    }

    with ThreadPoolExecutor(max_workers=STORE_WORKERS) as executor:
        # Lanzar las 3 llamadas al mismo tiempo
        futures = {
            executor.submit(fn, *args): store_name
            for store_name, (fn, args) in tasks.items()
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    prices.append(result)
            except Exception:
                pass  # Una tienda fallida no cancela las demás

    return prices


def _scrape_metacritic_parallel(title: str, platforms: list) -> list:
    """
    NIVEL 3: llama a Metacritic para cada plataforma en paralelo.
    Retorna lista de dicts de metacritic (solo los que no sean None).
    """
    mc_results = []

    with ThreadPoolExecutor(max_workers=len(platforms) or 1) as executor:
        futures = {
            executor.submit(scrape_metacritic, title, platform): platform
            for platform in platforms
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    mc_results.append(result)
            except Exception:
                pass

    return mc_results


def _process_game(game: dict) -> dict:
    """
    Procesa UN juego usando paralelismo en Nivel 2 y Nivel 3.
    Esta función la ejecuta cada proceso del Nivel 1.
    """
    title           = game["title"]
    platforms       = game.get("platforms", [])
    reference_price = game.get("reference_price", 0.0)

    result = {
        "title":           title,
        "platforms":       platforms,
        "reference_price": reference_price,
        "release_year":    game.get("release_year"),
        "genre":           game.get("genre"),
        "metacritic":      [],
        "hltb":            None,
        "prices":          [],
        "error":           False,
    }

    # Nivel 3: todas las plataformas de Metacritic al mismo tiempo
    result["metacritic"] = _scrape_metacritic_parallel(title, platforms)

    # HLTB no tiene paralelo (solo hay un resultado por juego)
    result["hltb"] = scrape_hltb(title)

    # Nivel 2: las 3 tiendas al mismo tiempo
    result["prices"] = _scrape_prices_parallel(title, reference_price)

    if not result["metacritic"] and not result["hltb"] and not result["prices"]:
        result["error"] = True

    return result


def run_parallel(games: list) -> tuple[list, float]:
    """
    Procesa la lista de juegos con 3 niveles de paralelismo.

    Parámetros:
        games — lista de dicts leída desde games.json

    Retorno:
        (results, elapsed_time) — mismo formato que run_linear
    """
    results    = []
    start_time = time.time()
    total      = len(games)

    # Nivel 1: varios juegos al mismo tiempo en procesos separados
    with ProcessPoolExecutor(max_workers=GAME_WORKERS) as executor:
        futures = {
            executor.submit(_process_game, game): game["title"]
            for game in games
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            title = futures[future]
            try:
                game_result = future.result()
                results.append(game_result)
                print(f"[Paralelo] {completed}/{total} — {title}")
            except Exception as e:
                # Si un juego falla completamente, igual lo registramos
                results.append({
                    "title": title,
                    "error": True,
                    "metacritic": [], "hltb": None, "prices": []
                })
                print(f"[Paralelo] {completed}/{total} — {title} (ERROR: {e})")

    elapsed = round(time.time() - start_time, 2)
    return results, elapsed