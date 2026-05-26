from metacritic import scrape_metacritic
from howlongtobeat import scrape_hltb

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


if __name__ == "__main__":
    test_metacritic()
    test_hltb()
    print("\n✓ Pruebas completadas.")  