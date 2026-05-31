from metacritic import scrape_metacritic
from howlongtobeat import scrape_hltb
from steam import scrape_steam
from amazon import scrape_amazon
from psstore import scrape_psstore

TEST_CASES_METACRITIC = [
    ("The Witcher 3: Wild Hunt", "PC"),
    ("Red Dead Redemption 2",    "PS4"),
    ("Hades",                    "Switch"),
    ("JuegoQueNoExiste XYZ",     "PC"),
]

TEST_CASES_HLTB = [
    "The Witcher 3: Wild Hunt",
    "Red Dead Redemption 2",
    "Hades",
    "JuegoQueNoExiste XYZ",
]


def separator(label):
    print("\n" + "=" * 50)
    print(f"  {label}")
    print("=" * 50)


def test_metacritic():
    separator("METACRITIC")
    for title, platform in TEST_CASES_METACRITIC:
        print(f"\n→ {title} [{platform}]")
        result = scrape_metacritic(title, platform)
        if result is None:
            print("   Resultado: None")
        else:
            print(f"   Metascore : {result['metascore']}")
            print(f"   User Score: {result['user_score']}")
            print(f"   URL       : {result['url']}")


def test_hltb():
    separator("HOW LONG TO BEAT")
    for title in TEST_CASES_HLTB:
        print(f"\n→ {title}")
        result = scrape_hltb(title)
        if result is None:
            print("   Resultado: None")
        else:
            print(f"   Main Story   : {result['main_story']} h")
            print(f"   Main + Extras: {result['main_extras']} h")
            print(f"   Completionist: {result['completionist']} h")
            print(f"   URL          : {result['url']}")


def _print_price_result(result):
    """Imprime los datos de precio de forma legible."""
    if result is None:
        print("   Resultado: None")
    else:
        print(f"   Tienda   : {result['store']}")
        print(f"   Precio   : ${result['current_price']}")
        print(f"   Original : ${result['original_price']}")
        print(f"   Descuento: {result['discount_pct']}%")
        print(f"   En oferta: {result['on_sale']}")
        print(f"   URL      : {result['url']}")


def test_steam():
    separator("STEAM")
    print("\n→ Hollow Knight")
    _print_price_result(scrape_steam("Hollow Knight", reference_price=14.99))


def test_amazon():
    separator("AMAZON")
    print("\n→ Hollow Knight")
    _print_price_result(scrape_amazon("Hollow Knight"))


def test_psstore():
    separator("PLAYSTATION STORE")
    print("\n→ Hollow Knight")
    _print_price_result(scrape_psstore("Hollow Knight"))


if __name__ == "__main__":
    test_metacritic()
    #test_hltb()
    test_steam()
    test_amazon()
    test_psstore()
    print("\n✓ Pruebas completadas.")  