import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DELAY_SECONDS = 1.5
WAIT_TIMEOUT = 10

def _get_driver() -> webdriver.Chrome:
 
    options = Options()
    options.add_argument("--headless")          # Sin ventana visible
    options.add_argument("--no-sandbox")        # Evita errores en entornos restringidos
    options.add_argument("--disable-dev-shm-usage")  # Evita problemas de memoria
    options.add_argument("--window-size=1920,1080")  # Resolución estándar
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )
    # Desactivar la detección de automatización de Amazon
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


def _parse_price(text: str) -> float | None:

    if not text:
        return None

    # Buscar un patrón numérico tipo "19.99" o "19,99"
    match = re.search(r"(\d+[\.,]?\d*)", text.replace(",", "."))
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            return None
    return None



def scrape_amazon(title: str) -> dict | None:
    driver = _get_driver()

    try:
        search_query = title.replace(" ", "+")
        search_url   = f"https://www.amazon.com/s?k={search_query}+game"

        time.sleep(DELAY_SECONDS)
        driver.get(search_url)

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            )
        )

        results = driver.find_elements(
            By.CSS_SELECTOR, "[data-component-type='s-search-result']"
        )

        if not results:
            return None

        for result in results:
            try:
                price_whole = result.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
                price_frac  = result.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text
                current_price = _parse_price(f"{price_whole}.{price_frac}")
            except Exception:
                # Este resultado no tiene precio visible → saltar al siguiente
                continue

            # Si no pudimos parsear el precio, saltar
            if current_price is None:
                continue

            # Intentar extraer el precio original (tachado)
            original_price = current_price  # Por defecto, mismo que el actual
            try:
                old_price_elements = result.find_elements(
                    By.CSS_SELECTOR, "span.a-price[data-a-strike='true'] span.a-offscreen"
                )
                if old_price_elements:
                    original_price = _parse_price(old_price_elements[0].text) or current_price
            except Exception:
                pass  # Si no hay precio original, dejamos el actual como referencia

            # Calcular el porcentaje de descuento
            if original_price > 0 and original_price > current_price:
                discount_pct = round((1 - current_price / original_price) * 100)
            else:
                discount_pct = 0

            on_sale = discount_pct > 0

           
            try:
                link_element = result.find_element(
                    By.CSS_SELECTOR, "a.a-link-normal.s-no-outline"
                )
                product_url = link_element.get_attribute("href") or ""
            except Exception:
                product_url = search_url  

           
            if "/dp/" in product_url:
                # Extraer solo la parte base: https://www.amazon.com/dp/ASIN
                dp_match = re.search(r"(https://www\.amazon\.com/[^?]*?/dp/[A-Z0-9]+)", product_url)
                if dp_match:
                    product_url = dp_match.group(1)


            return {
                "store":          "Amazon",
                "current_price":  current_price,
                "original_price": original_price,
                "discount_pct":   discount_pct,
                "on_sale":        on_sale,
                "url":            product_url,
            }

        return None

    except Exception:
        # Cualquier error inesperado retornamos None sin crashear
        return None

    finally:
        driver.quit()
