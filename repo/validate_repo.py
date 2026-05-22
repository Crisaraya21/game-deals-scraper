import json
import os

def validar_juegos():

    directorio_script = os.path.dirname(os.path.abspath(__file__))
    ruta_json = os.path.join(directorio_script, 'games.json')

    try:
        with open(ruta_json, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)
    except Exception as e:
        print(f"Error al cargar el archivo: {e}")
        return

    if not isinstance(datos, list):
        print("Error: games.json no contiene una lista en la raíz.")
        return

    campos_requeridos = ["title", "platforms", "reference_price", "release_year", "genre"]

    cantidad_validos = 0
    lista_errores = []

    for indice, juego in enumerate(datos):
        errores_juego = []

        if not isinstance(juego, dict):
            lista_errores.append(f"Entrada {indice}: No es un objeto válido.")
            continue

        campos_faltantes = [campo for campo in campos_requeridos if campo not in juego]
        if campos_faltantes:
            errores_juego.append(f"Faltan campos: {', '.join(campos_faltantes)}")

        if "platforms" in juego:
            plataformas = juego["platforms"]
            if not isinstance(plataformas, list) or len(plataformas) == 0:
                errores_juego.append("El campo 'platforms' debe ser una lista no vacía.")

        if "reference_price" in juego:
            precio = juego["reference_price"]
            if not isinstance(precio, (int, float)) or precio <= 0:
                errores_juego.append(f"El precio debe ser mayor a 0 (valor actual: {precio}).")


        if errores_juego:
            titulo = juego.get("title", f"Entrada {indice}")
            lista_errores.append(f"- {titulo}: " + " | ".join(errores_juego))
        else:
            cantidad_validos += 1


    print(f"Juegos válidos: {cantidad_validos}")
    print(f"Juegos con errores: {len(lista_errores)}")

    if lista_errores:
        print("\nJuegos con errores detallados:")
        for error in lista_errores:
            print(error)

if __name__ == "__main__":
    validar_juegos()
