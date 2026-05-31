"""
test_engines.py — prueba rápida de los dos motores con 1 juego.
Corre desde la raíz del proyecto: python test_engines.py
"""
import json
from engine.linear   import run_linear
from engine.parallel import run_parallel

def main():
    with open("repo/games.json") as f:
        games = json.load(f)[:1]  # solo 1 juego para ir rápido

    print(f"Probando con: {[g['title'] for g in games]}\n")

    # ── Lineal ──────────────────────────────────────────────────
    print("=" * 40)
    print("MOTOR LINEAL")
    print("=" * 40)
    results_l, tiempo_l = run_linear(games)
    exitosos_l = sum(1 for r in results_l if not r.get("error"))
    print(f"\nTiempo  : {tiempo_l}s")
    print(f"Exitosos: {exitosos_l}/{len(results_l)}")
    for r in results_l:
        print(f"  {r['title']}")
        for mc in r['metacritic']:
            print(f"    [{mc['platform']}] metascore={mc['metascore']} user={mc['user_score']}")
        print(f"    hltb       : {r['hltb']}")
        print(f"    precios    : {[p['store'] + ' $' + str(p['current_price']) for p in r['prices']]}")

    # ── Paralelo ─────────────────────────────────────────────────
    print("\n" + "=" * 40)
    print("MOTOR PARALELO")
    print("=" * 40)
    results_p, tiempo_p = run_parallel(games)
    exitosos_p = sum(1 for r in results_p if not r.get("error"))
    print(f"\nTiempo  : {tiempo_p}s")
    print(f"Exitosos: {exitosos_p}/{len(results_p)}")
    for r in results_p:
        print(f"  {r['title']}")
        print(f"    metacritic : {len(r['metacritic'])} entradas")
        print(f"    hltb       : {r['hltb']}")
        print(f"    precios    : {[p['store'] + ' $' + str(p['current_price']) for p in r['prices']]}")

    # ── Comparación ──────────────────────────────────────────────
    print("\n" + "=" * 40)
    if tiempo_p > 0:
        speedup = round(tiempo_l / tiempo_p, 2)
        print(f"Speedup: {speedup}x  (lineal {tiempo_l}s → paralelo {tiempo_p}s)")
    print("=" * 40)

if __name__ == "__main__":
    main()