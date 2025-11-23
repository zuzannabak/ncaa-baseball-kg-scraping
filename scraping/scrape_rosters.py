import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import json
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from parse_sidearm_view2_roster import parse_sidearm_roster_view2
import os  # dodaj, jeśli jeszcze nie ma

OUTPUT_DIR = "raw_schools"

# ---------- CONFIG: YOUR 20 SCHOOLS ----------

SCHOOLS = [
    {
        "school_name": "Duke University",
        "conference": "Atlantic Coast Conference (ACC)",
        "url": "https://goduke.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "Florida State University",
        "conference": "Atlantic Coast Conference (ACC)",
        "url": "https://seminoles.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "NC State University",
        "conference": "Atlantic Coast Conference (ACC)",
        "url": "https://gopack.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "University of Louisville",
        "conference": "Atlantic Coast Conference (ACC)",
        "url": "https://gocards.com/sports/baseball/roster",
        "season_year": 2024,
    },
    {
        "school_name": "University of North Carolina",
        "conference": "Atlantic Coast Conference (ACC)",
        "url": "https://goheels.com/sports/baseball/roster",
        "season_year": 2024,
    },
    {
        "school_name": "Cal Poly (California Polytechnic State University)",
        "conference": "Big West Conference",
        "url": "https://gopoly.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "CSUN (California State University, Northridge)",
        "conference": "Big West Conference",
        "url": "https://gomatadors.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },

    # --- TU ZACZYNAJĄ SIĘ 4 SZKOŁY ZE SPECJALNYM PARSEREM (VIEW2) ---
    {
        "school_name": "Cal State Fullerton (California State University, Fullerton)",
        "conference": "Big West Conference",
        "url": "https://fullertontitans.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "UC Santa Barbara (University of California, Santa Barbara)",
        "conference": "Big West Conference",
        "url": "https://ucsbgauchos.com/sports/baseball/roster/2024?view=2",
        "season_year": 2024,
    },
    {
        "school_name": "University of Evansville",
        "conference": "Missouri Valley Conference (MVC)",
        "url": "https://gopurpleaces.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "Wichita State University",
        "conference": "Missouri Valley Conference (MVC)",
        "url": "https://goshockers.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    # --- KONIEC 4 SPECJALNYCH ---

    {
        "school_name": "Creighton University",
        "conference": "Missouri Valley Conference (MVC)",
        "url": "https://gocreighton.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "Murray State University",
        "conference": "Missouri Valley Conference (MVC)",
        "url": "https://goracers.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "Oregon State University",
        "conference": "Pac-12 Conference",
        "url": "https://osubeavers.com/sports/baseball/roster",
        "season_year": 2026,  # strona pokazuje obecny roster jako 2026
    },
    {
        "school_name": "UCLA (University of California, Los Angeles)",
        "conference": "Pac-12 Conference",
        "url": "https://uclabruins.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "University of Washington",
        "conference": "Pac-12 Conference",
        "url": "https://gohuskies.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "Mississippi State University",
        "conference": "Southeastern Conference (SEC)",
        "url": "https://hailstate.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
    {
        "school_name": "University of Tennessee",
        "conference": "Southeastern Conference (SEC)",
        "url": "https://utsports.com/sports/baseball/roster/2024",
        "season_year": 2024,
    },
]



HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ZuzannaScraper/1.0)"
}

# ---------- BASIC HELPERS ----------

def ensure_view2(url: str) -> str:
    """
    Force ?view=2 if not already present.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "view" not in query:
        query["view"] = ["2"]
        new_query = urlencode(query, doseq=True)
        parsed = parsed._replace(query=new_query)
        return urlunparse(parsed)
    return url

def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

def normalize_space(s):
    if not s:
        return ""
    return " ".join(str(s).split())

# ---------- PARSING HELPERS FOR TEXT BLOCKS ----------

from bs4 import BeautifulSoup, NavigableString, Tag

def parse_pos_block(text: str):
    """
    Przykład:
    'Position C/1B Academic Year Gr.Height 6' 3'' Weight 225 lbs Custom Field 1 R/R'
    """
    position = class_year = height = weight = ""

    if "Position" not in text:
        return position, class_year, height, weight

    part = text.split("Position", 1)[1].strip()

    if "Academic Year" in part:
        position, part = part.split("Academic Year", 1)
        position = position.strip()
        part = part.strip()

    if "Height" in part:
        class_year, part = part.split("Height", 1)
        class_year = class_year.strip().rstrip(".")
        part = part.strip()

    if "Weight" in part:
        height, rest = part.split("Weight", 1)
        height = height.strip()
        weight = rest.strip()
        # wywalamy końcówkę 'Custom Field ...' jeśli jest
        if "Custom Field" in weight:
            weight = weight.split("Custom Field", 1)[0].strip()

    return position, class_year, height, weight


def parse_home_block(text: str):
    """
    Przykład:
    'Hometown Jackson, Tenn.Last School Memphis'
    """
    hometown = last_school = ""

    if "Hometown" not in text:
        return hometown, last_school

    part = text.split("Hometown", 1)[1].strip()

    if "Last School" in part:
        hometown, rest = part.split("Last School", 1)
        hometown = hometown.strip()
        last_school = rest.strip()
    else:
        hometown = part.strip()

    return hometown, last_school


def parse_player_from_jersey_anchor(jersey_anchor: Tag):
    """
    Dostaje <a>Jersey Number 24</a> i:
      - bierze numer koszulki,
      - z całej sekwencji elementów aż do następnego 'Jersey Number' składa tekst,
      - wyciąga imię, position/class/height/weight, hometown/last school.
    """
    # 1) numer
    jersey_text = normalize_space(jersey_anchor.get_text(" ", strip=True))
    jersey = jersey_text.split()[-1]  # '24'

    full_name = ""
    block_parts = []

    # 2) iterujemy przez wszystkie kolejne elementy w DOM,
    #    dopóki nie trafimy na kolejny 'Jersey Number' albo 'Coaching Staff'
    for elem in jersey_anchor.next_elements:
        if isinstance(elem, Tag) and elem.name == "a":
            t = normalize_space(elem.get_text(" ", strip=True))

            if t.startswith("Jersey Number"):
                # kolejny zawodnik -> koniec naszego bloku
                break

            # imię i nazwisko – pierwszy "normalny" link po jersey
            if not full_name and not t.startswith("Full Bio for") and not t.startswith("Expand for more info"):
                full_name = t
                block_parts.append(t)
                continue

            # resztę anchorów też dorzucamy do tekstu (może się przyda)
            block_parts.append(t)

        elif isinstance(elem, NavigableString):
            t = normalize_space(str(elem))
            if not t:
                continue
            if "Coaching Staff" in t:
                # koniec listy zawodników
                break
            block_parts.append(t)

    block_text = " ".join(block_parts)

    # 3) wyciągamy segment z Position... i Hometown...
    pos_segment = ""
    home_segment = ""

    if "Position" in block_text:
        start = block_text.find("Position")
        end_candidates = []
        for kw in ["Hometown", "Full Bio for", "Expand for more info about"]:
            idx = block_text.find(kw, start)
            if idx != -1:
                end_candidates.append(idx)
        end = min(end_candidates) if end_candidates else len(block_text)
        pos_segment = block_text[start:end].strip()

    if "Hometown" in block_text:
        start = block_text.find("Hometown")
        end_candidates = []
        for kw in ["Full Bio for", "Expand for more info about"]:
            idx = block_text.find(kw, start)
            if idx != -1:
                end_candidates.append(idx)
        end = min(end_candidates) if end_candidates else len(block_text)
        home_segment = block_text[start:end].strip()

    position, class_year, height, weight = parse_pos_block(pos_segment)
    hometown, last_school = parse_home_block(home_segment)

    return {
        "full_name": full_name,
        "jersey": jersey,
        "position": position,
        "class_year": class_year,
        "height": height,
        "weight": weight,
        "hometown": hometown,
        "last_school": last_school,
    }


def parse_sidearm_roster_accessible(soup: BeautifulSoup):
    """
    Główna funkcja: znajduje wszystkie 'Jersey Number X' i dla każdego
    wyciąga pełny blok zawodnika.
    """
    players = []
    anchors = soup.find_all("a")

    for a in anchors:
        txt = normalize_space(a.get_text(" ", strip=True))
        if not txt.startswith("Jersey Number"):
            continue

        player = parse_player_from_jersey_anchor(a)
        # wymagamy przynajmniej imienia
        if player["full_name"]:
            players.append(player)

    # deduplikacja (na wszelki wypadek)
    unique = {}
    for p in players:
        key = (p["full_name"], p["jersey"])
        if key not in unique:
            unique[key] = p

    return list(unique.values())


def parse_sidearm_roster(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # na razie pomijamy <table>, bo i tak wszystkie te rostery są w trybie listy
    players = parse_sidearm_roster_accessible(soup)
    return players


# ---------- ONTOLOGY JSON BUILDER ----------

def build_ontology_json_for_school(school_cfg, players):
    school_id = school_cfg["school_name"].replace(" ", "_")
    team_id = f"{school_id}_baseball_{school_cfg['season_year']}"
    conference_id = school_cfg["conference"].replace(" ", "_")
    season_id = str(school_cfg["season_year"])

    nodes = {
        "School": {
            "schoolId": school_id,
            "name": school_cfg["school_name"],
        },
        "Conference": {
            "conferenceId": conference_id,
            "conferenceName": school_cfg["conference"],
        },
        "Season": {
            "seasonId": season_id,
            "seasonYear": school_cfg["season_year"],
        },
        "Team": {
            "teamId": team_id,
            "teamName": f"{school_cfg['school_name']} Baseball",
        },
        "Players": [],
    }

    relationships = {
        "HAS_TEAM": [
            {"schoolId": school_id, "teamId": team_id}
        ],
        "MEMBER_OF": [
            {"schoolId": school_id, "conferenceId": conference_id}
        ],
        "PARTICIPATES_IN": [
            {"teamId": team_id, "seasonId": season_id}
        ],
        "PLAYS_FOR": [],
    }

    for idx, p in enumerate(players, start=1):
        player_id = f"{team_id}_player_{idx}"
        node_player = {
            "playerId": player_id,
            "fullName": p.get("full_name", ""),
            "classYear": p.get("class_year", ""),
            "position": p.get("position", ""),
            "height": p.get("height", ""),
            "weight": p.get("weight", ""),
            "hometown": p.get("hometown", ""),
            "jersey": p.get("jersey", ""),
            "lastSchool": p.get("last_school", ""),
        }
        nodes["Players"].append(node_player)
        relationships["PLAYS_FOR"].append(
            {"playerId": player_id, "teamId": team_id}
        )

    return {
        "School": nodes["School"],
        "Conference": nodes["Conference"],
        "Season": nodes["Season"],
        "Team": nodes["Team"],
        "Players": nodes["Players"],
        "Relationships": relationships,
    }

# ---------- MAIN DRIVER ----------

def main():
    all_schools_data = []

    # utwórz katalog na surowe pliki z rosterami
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # szkoły, które lecą przez parser 2 (parser_sidearm_view2)
    special_layout_schools = {
        "Wichita State University",
        "University of Evansville",
        "UC Santa Barbara (University of California, Santa Barbara)",
        "Cal State Fullerton (California State University, Fullerton)",
    }

    for school in SCHOOLS:
        print(f"\n=== {school['school_name']} ===")
        roster_url = ensure_view2(school["url"])
        print(f"Fetching: {roster_url}")

        try:
            html = fetch_html(roster_url)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch {roster_url}: {e}")
            continue

        # WYBÓR PARSERA: 1 (jersey) albo 2 (view2)
        if school["school_name"] in special_layout_schools:
            # parser 2 – obsługa trudniejszych layoutów (Wichita, Evansville, UCSB, Fullerton)
            players = parse_sidearm_roster_view2(html)
        else:
            # parser 1 – klasyczny layout sidearm z 'Jersey Number ...'
            players = parse_sidearm_roster(html)

        print(f"  Parsed {len(players)} players")

        # quick debug: print first 3 players
        for p in players[:3]:
            print(
                "   -",
                p.get("jersey", ""),
                p.get("full_name", ""),
                "| pos:", p.get("position", ""),
                "| class:", p.get("class_year", ""),
                "| h:", p.get("height", ""),
                "| htwn:", p.get("hometown", ""),
            )

        school_json = build_ontology_json_for_school(school, players)
        all_schools_data.append(school_json)

        # ---- ZMIANA TUTAJ: zapis do katalogu raw_schools ----
        safe_name = school["school_name"].replace(" ", "_").replace("/", "_")
        filename = f"{safe_name.lower()}_baseball_{school['season_year']}_ontology.json"
        out_path = os.path.join(OUTPUT_DIR, filename)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(school_json, f, indent=2, ensure_ascii=False)
        print(f"  Saved to {out_path}")

    # plik zbiorczy zostaje w katalogu głównym
    with open("all_schools_ontology.json", "w", encoding="utf-8") as f:
        json.dump(all_schools_data, f, indent=2, ensure_ascii=False)
    print("\nDone. Wrote all_schools_ontology.json")


if __name__ == "__main__":
    main()
