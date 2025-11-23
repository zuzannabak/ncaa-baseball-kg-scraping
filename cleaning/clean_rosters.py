import json
import os
import re

INPUT_PATH = "all_schools_ontology.json"
OUTPUT_PATH = "all_schools_ontology_clean.json"
PER_SCHOOL_DIR = "clean_schools"  # opcjonalnie: osobne pliki per uczelnia


def normalize_height(h: str) -> str:
    """
    Normalizuje height do formatu F-I, np.:
      "6' 2''"  -> "6-2"
      "6'2\""   -> "6-2"
      "6-2"     -> "6-2"
      "-"       -> ""
    """
    if not h:
        return ""

    h = h.strip()
    if h == "-":
        return ""

    # ujednolicenia znaków
    h = h.replace("′", "'").replace("–", "-").replace("—", "-")

    # przypadek typu 6' 2'' / 6'2"
    # najpierw wywal końcówki z podwójnym apostrofem / cudzysłowem
    tmp = h.replace("''", "").replace('"', "")
    tmp = tmp.replace(" ", "")

    if "'" in tmp:
        # np. "6'2"
        feet, inches = tmp.split("'", 1)
        if feet.isdigit() and inches.isdigit():
            return f"{feet}-{inches}"

    # przypadek typu 6-2, 6 - 2
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", h)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    # zostaw jak jest, jeśli nic nie pasuje
    return h


def normalize_weight(w: str):
    """
    Normalizuje weight do:
      - string: "NNN lbs"
      - liczba: NNN (int) jako weightLbs
    Jeżeli nie znajdzie liczby -> ("", None)
    """
    if not w:
        return "", None

    m = re.search(r"(\d+)", w)
    if not m:
        return "", None

    val = int(m.group(1))
    return f"{val} lbs", val


def split_hometown_lastschool(hometown: str, last_school: str):
    """
    Jeżeli lastSchool jest puste, a hometown ma " / ",
    rozdziel to na:
      - hometown (przed " / ")
      - lastSchool (po " / ")
    W przeciwnym razie nie zmieniaj.
    """
    if last_school or not hometown:
        return hometown, last_school

    if " / " in hometown:
        before, after = hometown.split(" / ", 1)
        return before.strip(), after.strip()

    return hometown, last_school


def clean_player(player: dict) -> dict:
    """
    Zwraca nowego (lub zmodyfikowanego) playera z:
      - height w formacie F-I
      - weight w formacie "NNN lbs" + weightLbs (int)
      - poprawionym hometown / lastSchool gdy trzeba
    """
    # height
    h = player.get("height", "")
    player["height"] = normalize_height(h)

    # weight
    w = player.get("weight", "")
    weight_str, weight_num = normalize_weight(w)
    player["weight"] = weight_str
    # opcjonalne dodatkowe pole liczbowe
    player["weightLbs"] = weight_num

    # hometown / lastSchool (tylko jeśli lastSchool puste, a hometown ma " / ")
    hometown = player.get("hometown", "")
    last_school = player.get("lastSchool", "")
    hometown, last_school = split_hometown_lastschool(hometown, last_school)
    player["hometown"] = hometown
    player["lastSchool"] = last_school

    return player


def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Nie znalazłam pliku {INPUT_PATH}")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        all_schools = json.load(f)

    # upewnij się, że mamy listę szkół
    if not isinstance(all_schools, list):
        raise ValueError("Oczekiwałam listy szkół w all_schools_ontology.json")

    cleaned = []

    for school in all_schools:
        school_name = school.get("School", {}).get("name", "UNKNOWN")
        players = school.get("Players", [])

        new_players = []
        for p in players:
            new_players.append(clean_player(p.copy()))

        school["Players"] = new_players
        cleaned.append(school)

    # zapis całości
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Zapisano oczyszczone dane do: {OUTPUT_PATH}")

    # opcjonalnie: zapisz osobne pliki per szkoła (w podobnym formacie jak wcześniej)
    os.makedirs(PER_SCHOOL_DIR, exist_ok=True)
    for school in cleaned:
        name = school["School"]["name"]
        season_year = school["Season"]["seasonYear"]
        safe_name = name.replace(" ", "_").replace("/", "_")
        out_path = os.path.join(
            PER_SCHOOL_DIR,
            f"{safe_name.lower()}_baseball_{season_year}_ontology_clean.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(school, f, indent=2, ensure_ascii=False)

    print(f"Oczyszczone pliki per szkoła zapisane w katalogu: {PER_SCHOOL_DIR}")


if __name__ == "__main__":
    main()
