"""
engine/linear.py
----------------
Motor secuencial: procesa cada juego uno por uno, en orden.
Sirve como referencia de rendimiento para comparar con el motor paralelo.
"""

import time
import sys
import os

# Agregar la raíz del proyecto al path para poder importar scrapers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.metacritic   import scrape_metacritic
from scrapers.howlongtobeat import scrape_hltb
from scrapers.steam        import scrape_steam
from scrapers.amazon       import scrape_amazon
from scrapers.psstore      import scrape_psstore


def _process_game(game: dict) -> dict:
    """
    Llama a todos los scrapers para UN juego de forma secuencial.
    Retorna un dict con todos los datos recolectados.
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
        "metacritic":      [],   # una entrada por plataforma
        "hltb":            None,
        "prices":          [],   # una entrada por tienda
        "error":           False,
    }

    # ── 1. Metacritic: una llamada por cada plataforma del juego ──
    for platform in platforms:
        mc = scrape_metacritic(title, platform)
        if mc:
            result["metacritic"].append(mc)

    # ── 2. HowLongToBeat ──
    result["hltb"] = scrape_hltb(title)

    # ── 3. Tiendas de precio ──
    steam_data = scrape_steam(title, reference_price)
    if steam_data:
        result["prices"].append(steam_data)

    amazon_data = scrape_amazon(title)
    if amazon_data:
        result["prices"].append(amazon_data)

    ps_data = scrape_psstore(title)
    if ps_data:
        result["prices"].append(ps_data)

    # Marcar como fallido si no se obtuvo ningún dato útil
    if not result["metacritic"] and not result["hltb"] and not result["prices"]:
        result["error"] = True

    return result


def run_linear(games: list) -> tuple[list, float]:
    """
    Procesa la lista de juegos de forma completamente secuencial.

    Parámetros:
        games — lista de dicts leída desde games.json

    Retorno:
        (results, elapsed_time)
        - results: lista de dicts, uno por juego
        - elapsed_time: segundos que tardó en total
    """
    results    = []
    start_time = time.time()

    for i, game in enumerate(games, start=1):
        print(f"[Lineal] {i}/{len(games)} — {game['title']}")
        game_result = _process_game(game)
        results.append(game_result)

    elapsed = round(time.time() - start_time, 2)
    return(results, elapsed)