import time
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

SEARCH_URL  = "https://store.steampowered.com/api/storesearch/"
DETAILS_URL = "https://store.steampowered.com/api/appdetails"

def _search_appid(title: str) -> int | None:
    time.sleep(DELAY_SECONDS)

    try:
        response = requests.get(
            SEARCH_URL,
            params={"term": title, "l": "english", "cc": "us"},
            headers=HEADERS,
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    # La API devuelve una lista en la clave "items"
    items = data.get("items", [])
    if not items:
        return None

    # Tomamos el appid del primer resultado (el más relevante)
    return items[0].get("id")


def _get_price_data(appid: int) -> dict | None:
    time.sleep(DELAY_SECONDS)

    try:
        response = requests.get(
            DETAILS_URL,
            params={"appids": appid, "cc": "us", "filters": "price_overview"},
            headers=HEADERS,
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    app_data = data.get(str(appid), {})

    if not app_data.get("success"):
        return None

    price_overview = app_data.get("data", {}).get("price_overview")
    if not price_overview:
        return None

    return price_overview

def scrape_steam(title: str, reference_price: float = 0.0) -> dict | None:


    appid = _search_appid(title)
    if appid is None:
        return None

    # Obtener los datos de precio
    price_data = _get_price_data(appid)
    if price_data is None:
        return None

    # Steam devuelve los precios en centavos (ej. 1499 = $14.99)
    current_cents  = price_data.get("final", 0)
    original_cents = price_data.get("initial", 0)
    discount_pct   = price_data.get("discount_percent", 0)

    # Convertimos de centavos a dólares con 2 decimales
    current_price  = round(current_cents / 100, 2)
    original_price = round(original_cents / 100, 2)

    # Determinar si está en oferta 
    if discount_pct > 0:
        on_sale = True
    elif reference_price > 0 and current_price < reference_price:
        on_sale = True
    else:
        on_sale = False

    # retornar el resultado
    return {
        "store":          "Steam",
        "current_price":  current_price,
        "original_price": original_price,
        "discount_pct":   discount_pct,
        "on_sale":        on_sale,
        "url":            f"https://store.steampowered.com/app/{appid}",
    }
