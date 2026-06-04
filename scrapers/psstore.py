import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# Pausa entre peticiones para no saturar los servidores
DELAY_SECONDS = 1.5

# Tiempo máximo (segundos) que Selenium esperará la carga de elementos
WAIT_TIMEOUT = 10

# Headers que simulan un navegador real
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# URL base de búsqueda en PS Store (región US / inglés)
PS_SEARCH_URL = "https://store.playstation.com/en-us/search/"


def _parse_price(text: str) -> float | None:
    if not text:
        return None

    text = text.strip().lower()
    if "free" in text:
        return 0.0
    match = re.search(r"(\d+\.?\d*)", text.replace(",", ""))
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            return None
    return None


def _get_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chromedriver_path = os.path.join(root_dir, "chromedriver.exe")
    if os.path.exists(chromedriver_path):
        service = Service(executable_path=chromedriver_path)
    else:
        service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def _build_result(current_price: float,
                  original_price: float,
                  product_url: str) -> dict:
    if original_price > 0 and original_price > current_price:
        discount_pct = round((1 - current_price / original_price) * 100)
    else:
        discount_pct = 0

    on_sale = discount_pct > 0

    return {
        "store":          "PlayStation Store",
        "current_price":  current_price,
        "original_price": original_price,
        "discount_pct":   discount_pct,
        "on_sale":        on_sale,
        "url":            product_url,
    }


# ──────────────────────────────────────────────
# Método 1: requests + BeautifulSoup
# ──────────────────────────────────────────────

def _scrape_with_requests(title: str) -> dict | None:
    time.sleep(DELAY_SECONDS)
    search_url = PS_SEARCH_URL + title.replace(" ", "%20")

    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "lxml")

    product_links = soup.find_all("a", href=re.compile(r"/en-us/product/"))
    if not product_links:
        return None

    first_link = product_links[0]
    product_url = "https://store.playstation.com" + first_link.get("href", "")
    price_spans = first_link.find_all("span", string=re.compile(r"\$\d+"))

    if not price_spans:
        return None
    current_price = _parse_price(price_spans[0].text)
    if current_price is None:
        return None

    if len(price_spans) >= 2:
        original_price = _parse_price(price_spans[1].text) or current_price
    else:
        original_price = current_price

    return _build_result(current_price, original_price, product_url)



def _scrape_with_selenium(title: str) -> dict | None:
    """
    Usa Selenium para abrir Chrome, navegar a PS Store, esperar que
    cargue el JavaScript, y extraer los precios del primer resultado.
    Se usa cuando requests + BeautifulSoup no pudo obtener datos.
    """
    driver = _get_driver()

    try:
        # Navegar a la página de búsqueda
        search_url = PS_SEARCH_URL + title.replace(" ", "%20")

        time.sleep(DELAY_SECONDS)
        driver.get(search_url)

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='/product/']")
            )
        )

        time.sleep(2)

        # Obtener el primer enlace a un producto
        product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        if not product_links:
            return None

        product_url = product_links[0].get_attribute("href") or ""

        # Extraer todos los textos con formato de precio ($XX.XX)
        # dentro del primer enlace de producto
        first_card = product_links[0]
        spans = first_card.find_elements(By.TAG_NAME, "span")

        prices_found = []
        for span in spans:
            span_text = span.text.strip()
            if span_text and re.search(r"\$\d+", span_text):
                parsed = _parse_price(span_text)
                if parsed is not None:
                    prices_found.append(parsed)

        if not prices_found:
            return None

        # El primer precio encontrado es el precio actual
        current_price = prices_found[0]

        # Si hay un segundo precio, es el original (sin descuento)
        original_price = prices_found[1] if len(prices_found) >= 2 else current_price

        if original_price < current_price:
            current_price, original_price = original_price, current_price

        return _build_result(current_price, original_price, product_url)

    except Exception:
        return None

    finally:
        driver.quit()


# ──────────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────────

def scrape_psstore(title: str) -> dict | None:
    """
    Busca un juego en PlayStation Store y retorna su información de precio.

    Estrategia:
      1. Intenta primero con requests + BeautifulSoup (rápido).
      2. Si falla, usa Selenium como fallback (más lento pero confiable).

    Parámetros:
        title — Nombre del juego a buscar (ej. "Hollow Knight")

    Retorno:
        Un diccionario con los datos de precio, o None si no se encontró.
        Ejemplo:
        {
            "store": "PlayStation Store",
            "current_price": 14.99,
            "original_price": 29.99,
            "discount_pct": 50,
            "on_sale": True,
            "url": "https://store.playstation.com/..."
        }
    """
    # Intento 1: requests + BeautifulSoup 
    result = _scrape_with_requests(title)
    if result is not None:
        return result

    # Intento 2: Selenium
    return _scrape_with_selenium(title)
