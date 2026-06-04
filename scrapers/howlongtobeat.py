import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DELAY_SECONDS     = 1.5

def _get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def _parse_time(text: str) -> float | None:
    try:
        text = text.lower()
        text = text.replace("hours", "").replace("hour", "").strip()
        text = text.replace("½", ".5").replace("¼", ".25").replace("¾", ".75")
        return round(float(text), 1)
    except (ValueError, AttributeError):
        return None


def scrape_hltb(title: str) -> dict | None:
    driver = _get_driver()
    result = None

    try:
        # 1) Buscar el juego — tomar el primer href con /game/
        driver.get(f"https://howlongtobeat.com/?q={title.replace(' ', '+')}")
        time.sleep(6)

        # Buscar cualquier link a /game/ (con o sin texto)
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'/game/')]")
        game_url = None
        for l in links:
            href = l.get_attribute("href") or ""
            # Filtrar solo links tipo /game/NÚMERO (no forum, reviews, etc.)
            import re
            if re.match(r"https://howlongtobeat\.com/game/\d+$", href):
                game_url = href
                break

        if not game_url:
            return None

        # 2) Ir a la página del juego
        driver.get(game_url)
        time.sleep(3)

        # 3) Extraer tiempos
        times = {}
        stats = driver.find_elements(By.XPATH, "//div[contains(@class,'stat')]")
        for stat in stats:
            try:
                label = stat.find_element(By.TAG_NAME, "h4").text.strip()
                value = stat.find_element(By.TAG_NAME, "h5").text.strip()
                if label in ("Main Story", "Main + Sides", "Completionist"):
                    times[label] = _parse_time(value)
            except Exception:
                continue

        result = {
            "main_story":    times.get("Main Story"),
            "main_extras":   times.get("Main + Sides"),
            "completionist": times.get("Completionist"),
            "url":           game_url,
        }

    except Exception:
        result = None
    finally:
        driver.quit()

    return result