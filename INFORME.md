# Informe del Proyecto: Game Deals Scraper

## 1. Descripción general del sistema
El **Game Deals Scraper** es una herramienta automatizada diseñada para consultar múltiples sitios web (tiendas de distribución digital y páginas de reseñas) y consolidar la información de precios y calificaciones de un catálogo de videojuegos en un solo lugar. 

El objetivo académico principal de este proyecto es demostrar cómo la implementación de **paralelismo y concurrencia** (mediante procesos e hilos) puede optimizar drásticamente operaciones limitadas por I/O, como lo es el Web Scraping.

## 2. Arquitectura y módulos
La estructura del proyecto está organizada de forma modular:

- **`engine/`**: Contiene la lógica central de ejecución.
  - `linear.py`: Motor secuencial que procesa juego por juego, útil como línea base de rendimiento.
  - `parallel.py`: Motor concurrente que implementa tres niveles de paralelismo para acelerar el proceso.
- **`scrapers/`**: Carpeta donde residen los scripts de extracción para cada página web (`amazon.py`, `steam.py`, `psstore.py`, `metacritic.py`, `howlongtobeat.py`).
- **`generator/`**: 
  - `html_builder.py`: Se encarga de procesar los resultados recolectados (en `results.json`) y generar la interfaz web final (`index.html`) con los estilos y gráficos inyectados.
- **`main.py`**: El punto de entrada principal del programa que gestiona los argumentos por consola (modo, límite) y orquesta la ejecución.
- **`repo/`**: Contiene el archivo fuente de entrada (`games.json`) con la lista de juegos a procesar.
- **`output/`**: Directorio donde se guardan los resultados finales (`results.json` y `index.html`).

## 3. Los 3 niveles de paralelismo
El motor paralelo (`engine/parallel.py`) fue diseñado con una arquitectura concurrente de 3 capas para aprovechar al máximo los recursos sin bloquear el sistema:

1. **Nivel 1 (Procesos paralelos por juego):**
   Utiliza `ProcessPoolExecutor` para procesar múltiples juegos al mismo tiempo usando procesos separados del sistema operativo. Por defecto, analiza hasta 4 juegos de la lista a la vez, sorteando el límite global del GIL de Python.
   ```python
   with ProcessPoolExecutor(max_workers=GAME_WORKERS) as executor:
       futures = {executor.submit(_process_game, game): game["title"] for game in games}
   ```

2. **Nivel 2 (Hilos concurrentes por tienda):**
   Al investigar un juego específico, el proceso invoca un `ThreadPoolExecutor` para hacer peticiones simultáneas a Steam, Amazon y PlayStation Store. Al ser operaciones I/O-bound (esperando red), los hilos son sumamente eficientes.
   ```python
   with ThreadPoolExecutor(max_workers=STORE_WORKERS) as executor:
       futures = {executor.submit(fn, *args): store_name for store_name, (fn, args) in tasks.items()}
   ```

3. **Nivel 3 (Hilos concurrentes por plataforma):**
   Ya que un juego puede tener reseñas para PC, PS5, Xbox, etc., en Metacritic, se despliega otro `ThreadPoolExecutor` que lanza una petición HTTP por cada plataforma registrada para el mismo juego, todas de forma paralela.
   ```python
   with ThreadPoolExecutor(max_workers=len(platforms) or 1) as executor:
       futures = {executor.submit(scrape_metacritic, title, platform): platform for platform in platforms}
   ```

## 4. Resultados de tiempo obtenidos
*(Nota: Los resultados de las pruebas de 30 y 50 juegos se actualizarán al finalizar las pruebas de carga).*

| N juegos | Tiempo lineal | Tiempo paralelo | Speedup |
|----------|---------------|-----------------|---------|
| 2        | 85.07s        | 21.32s          | 3.99x   |
| 30       |               |                 |         |
| 50       |               |                 |         |

## 5. Dificultades encontradas
Durante el desarrollo del Scraper nos topamos con varios obstáculos típicos de extracción web:
- **Bloqueos y detección de bots:** Amazon y PS Store a veces bloqueaban solicitudes automáticas, arrojando errores 403 o congelándose. Esto se resolvió utilizando cabeceras realistas (User-Agent modificado) y pasando configuraciones en ChromeOptions (`--disable-blink-features=AutomationControlled`).
- **Problemas con el manejador web (WebDriverManager):** El programa sufría "cuellos de botella" infinitos cuando la API de Google fallaba al descargar `chromedriver`. Se arregló implementando una validación condicional (fallback) para que los scrapers puedan detectar y usar el ejecutable de ChromeDriver localmente en primer lugar.
- **Cambios e inconsistencias de estructura HTML:** Algunos juegos tenían los precios en elementos no estándar o usaban precios variables (tachados). Se implementaron selectores CSS y Regex más flexibles para asegurar la lectura.

## 6. Conclusiones
La implementación del paralelismo fue **un éxito indiscutible**, reportando velocidades de casi **400% (4x)** por sobre la solución secuencial.

La técnica de **Paralelismo Combinado** es crucial cuando se lidia con la red. Ejecutar código secuencialmente (Modo Lineal) es inviable a escala, pues procesar catálogos grandes tomaría horas si hay que esperar a que cada página web de cada tienda responda por turnos. El modo paralelo, sin embargo, logra aislar todas esas pausas y resolverlas al mismo tiempo, lo que comprueba que cuando hay cuellos de botella por operaciones I/O-bound (red, descargas), el uso intensivo de **Hilos (Threading) + Multipocesamiento (Multiprocessing)** es la estrategia óptima a seguir.
