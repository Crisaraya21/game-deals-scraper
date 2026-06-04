import json
import argparse
import os
import sys
from datetime import datetime

from engine.linear import run_linear
from engine.parallel import run_parallel
from generator import html_builder

def main():
    try:
        with open("repo/games.json", "r", encoding="utf-8") as f:
            games = json.load(f)
    except FileNotFoundError:
        print("Error: El archivo repo/games.json no existe.")
        sys.exit(1)

    # Argparse
    parser = argparse.ArgumentParser(description="Game Deals Scraper")
    parser.add_argument('--mode', type=str, choices=['linear', 'parallel', 'both'], default='both', help='Modo de ejecución (default: both)')
    parser.add_argument('--limit', type=int, default=None, help="primeros N juegos a procesar")
    args = parser.parse_args()


    if args.limit is not None:
        games = games[:args.limit]

    #Lógica de sobreescritura
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    results_path = os.path.join(output_dir, "results.json")

    if os.path.exists(results_path):
        resp = input(f"El archivo {results_path} ya existe. ¿Sobreescribir? (s/n): ").strip().lower()
        if resp != "s":
            print("Cargando resultados existentes y generando HTML...")
            with open(results_path, "r", encoding="utf-8") as f:
                results_data = json.load(f)
            
            if hasattr(html_builder, 'build'):
                html_builder.build(results_data)
            else:
                print("Nota: html_builder.build no está implementado aún.")
            sys.exit(0)
        else:
            print("Sobreescribiendo results.json...")


    results = []
    linear_time = None
    parallel_time = None

    if args.mode == "linear":
        results, linear_time = run_linear(games)
    elif args.mode == "parallel":
        results, parallel_time = run_parallel(games)
    elif args.mode == "both":
        results, linear_time = run_linear(games)
        results, parallel_time = run_parallel(games)

    # Calcular estadísticas
    successful = 0
    failed = 0

    for game in results:
        # Se asume exitoso si 'error' es False
        if not game.get("error", True):
            successful += 1
        else:
            failed += 1

    speedup = None
    if linear_time is not None and parallel_time is not None and parallel_time > 0:
        speedup = linear_time / parallel_time


    print("\n===== RESULTADOS =====")
    print(f"Juegos procesados : {len(results)}")
    print(f"Exitosos          : {successful}")
    print(f"Fallidos          : {failed}")
    if linear_time is not None:
        print(f"Tiempo lineal     : {linear_time:.2f}s")
    if parallel_time is not None:
        print(f"Tiempo paralelo   : {parallel_time:.2f}s")
    if speedup is not None:
        print(f"Speedup obtenido  : {speedup:.2f}x")
    print("======================\n")

    # Guardar results.json
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_games": len(games),
        "successful": successful,
        "failed": failed,
        "linear_time": linear_time,
        "parallel_time": parallel_time,
        "speedup": speedup,
        "games": results
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"Resultados guardados en {results_path}")

    # html_builder de forma preventiva
    if hasattr(html_builder, 'build'):
        html_builder.build(output_data)

if __name__ == "__main__":
    main()