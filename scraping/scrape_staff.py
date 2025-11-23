# staff_scraper.py

import json
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ZuzannaStaffScraper/1.0)"
}

OUTPUT_DIR = "raw_staff"

# --- 1) KONFIGURACJA SZKÓŁ -------------------------------------------------

@dataclass
class SchoolConfig:
    school_name: str
    conference: str
    season_year: int
    roster_url: str
    staff_url: Optional[str] = None  # jeśli None, użyj roster_url


SCHOOLS: List[SchoolConfig] = [
    # ACC
    SchoolConfig(
        "Duke University",
        "Atlantic Coast Conference (ACC)",
        2024,
        roster_url="https://goduke.com/sports/baseball/roster/2024",
        staff_url="https://goduke.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "Florida State University",
        "Atlantic Coast Conference (ACC)",
        2024,
        roster_url="https://seminoles.com/sports/baseball/roster/2024",
        staff_url="https://seminoles.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "NC State University",
        "Atlantic Coast Conference (ACC)",
        2024,
        roster_url="https://gopack.com/sports/baseball/roster/2024",
        staff_url="https://gopack.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "University of Louisville",
        "Atlantic Coast Conference (ACC)",
        2024,
        roster_url="https://gocards.com/sports/baseball/roster",
        staff_url="https://gocards.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "University of North Carolina",
        "Atlantic Coast Conference (ACC)",
        2024,
        roster_url="https://goheels.com/sports/baseball/roster",
        staff_url="https://goheels.com/sports/baseball/coaches",
    ),

    # Big West
    SchoolConfig(
        "Cal Poly (California Polytechnic State University)",
        "Big West Conference",
        2024,
        roster_url="https://gopoly.com/sports/baseball/roster/2024",
        staff_url="https://gopoly.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "Cal State Fullerton (California State University, Fullerton)",
        "Big West Conference",
        2024,
        roster_url="https://fullertontitans.com/sports/baseball/roster/2024",
        staff_url="https://fullertontitans.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "CSUN (California State University, Northridge)",
        "Big West Conference",
        2024,
        roster_url="https://gomatadors.com/sports/baseball/roster/2024",
        staff_url="https://gomatadors.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "UC Santa Barbara (University of California, Santa Barbara)",
        "Big West Conference",
        2024,
        roster_url="https://ucsbgauchos.com/sports/baseball/roster/2024",
        staff_url="https://ucsbgauchos.com/sports/baseball/coaches",
    ),

    # MVC
    SchoolConfig(
        "Creighton University",
        "Missouri Valley Conference (MVC)",
        2024,
        roster_url="https://gocreighton.com/sports/baseball/roster/2024",
        staff_url="https://gocreighton.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "Murray State University",
        "Missouri Valley Conference (MVC)",
        2024,
        roster_url="https://goracers.com/sports/baseball/roster/2024",
        staff_url="https://goracers.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "University of Evansville",
        "Missouri Valley Conference (MVC)",
        2024,
        roster_url="https://gopurpleaces.com/sports/baseball/roster/2024",
        staff_url="https://gopurpleaces.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "Wichita State University",
        "Missouri Valley Conference (MVC)",
        2024,
        roster_url="https://goshockers.com/sports/baseball/roster/2024",
        staff_url="https://goshockers.com/sports/baseball/coaches",
    ),

    # Pac-12 / etc.
    SchoolConfig(
        "Oregon State University",
        "Pac-12 Conference",
        2026,  # ich aktualny roster jest 2026, ale staff i tak jest spójny
        roster_url="https://osubeavers.com/sports/baseball/roster",
        staff_url="https://osubeavers.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "UCLA (University of California, Los Angeles)",
        "Pac-12 Conference",
        2024,
        roster_url="https://uclabruins.com/sports/baseball/roster/2024",
        staff_url="https://uclabruins.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "University of Washington",
        "Pac-12 Conference",
        2024,
        roster_url="https://gohuskies.com/sports/baseball/roster/2024",
        staff_url="https://gohuskies.com/sports/baseball/coaches",
    ),

    # SEC
    SchoolConfig(
        "Mississippi State University",
        "Southeastern Conference (SEC)",
        2024,
        roster_url="https://hailstate.com/sports/baseball/roster/2024",
        staff_url="https://hailstate.com/sports/baseball/coaches",
    ),
    SchoolConfig(
        "University of Tennessee",
        "Southeastern Conference (SEC)",
        2024,
        roster_url="https://utsports.com/sports/baseball/roster/2024",
        staff_url="https://utsports.com/sports/baseball/coaches",
    ),
]


# --- 2) HELPERY HTTP / HTML -------------------------------------------------

def ensure_view2(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "view" not in query:
        query["view"] = ["2"]
        new_query = urlencode(query, doseq=True)
        parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.text


def normalize_space(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.split())


# --- 3) PARSOWANIE STAFFU ---------------------------------------------------

def classify_role(title: str) -> str:
    """
    Heurystycznie: czy to coach czy support staff?
    """
    t = title.lower()
    if "coach" in t:
        return "coach"
    # typowe support roles
    support_keywords = [
        "director",
        "operations",
        "analyst",
        "coordinator",
        "trainer",
        "strength",
        "performance",
        "athletic",
        "development",
        "nutrition",
        "video",
        "equipment",
        "mental",
    ]
    if any(k in t for k in support_keywords):
        return "support"
    # fallback: traktuj jako coach
    return "coach"


def parse_staff_from_table(table) -> List[Tuple[str, str]]:
    """
    Szuka wierszy typu [Name, Title, ...].
    Zwraca listę (name, title).
    """
    staff = []
    headers = [normalize_space(th.get_text()) for th in table.find_all("th")]
    name_idx = None
    title_idx = None

    for i, h in enumerate(headers):
        hl = h.lower()
        if name_idx is None and ("name" in hl or "coach" in hl):
            name_idx = i
        if title_idx is None and ("title" in hl or "position" in hl or "role" in hl):
            title_idx = i

    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        # jeśli nie ma nagłówków, spróbuj prosto: [Name, Title]
        if name_idx is None or title_idx is None:
            if len(cells) < 2:
                continue
            name = normalize_space(cells[0].get_text())
            title = normalize_space(cells[1].get_text())
        else:
            if name_idx >= len(cells) or title_idx >= len(cells):
                continue
            name = normalize_space(cells[name_idx].get_text())
            title = normalize_space(cells[title_idx].get_text())

        if not name or not title:
            continue
        # wywalamy wiersze z nagłówkami
        if name.lower() in ("name", "coach", "head coach"):
            continue
        staff.append((name, title))

    return staff


def parse_staff_generic_block(block) -> List[Tuple[str, str]]:
    """
    Ogólny fallback: w danym fragmencie DOM szukamy elementów,
    które wyglądają jak 'Imię Nazwisko' + 'Tytuł'.

    Heurystyka:
      - link <a> z href zawierającym 'coaches' lub 'staff-directory' -> name
      - tytuł w tym samym elemencie lub w następnym.
    """
    staff = []

    # 1) sprawdź 'osoby' jako linki do coach profile
    for a in block.find_all("a", href=True):
        href = a["href"].lower()
        if "coach" in href or "coaches" in href or "staff-directory" in href:
            name = normalize_space(a.get_text())
            if not name:
                continue

            # tytuł: ten sam <a> + rodzeństwo / rodzic
            title = ""
            # tekst w tym samym elemencie (np. <p>Imię – Title</p>)
            parent_text = normalize_space(a.parent.get_text(" "))
            # wytnij samo imię z parent_text
            if parent_text and len(parent_text) > len(name):
                # spróbuj: po imieniu część to title
                idx = parent_text.find(name)
                if idx != -1:
                    after = parent_text[idx + len(name):].strip(" -–,")
                    # ogranicz długość, żeby nie brać całego akapitu
                    if 0 < len(after) < 120:
                        title = after

            if not title:
                # poszukaj w następnym rodzeństwie
                sib = a.parent.next_sibling
                if sib and hasattr(sib, "get_text"):
                    sib_text = normalize_space(sib.get_text(" "))
                    if sib_text and 0 < len(sib_text) < 120:
                        title = sib_text

            if name and title:
                staff.append((name, title))

    # 2) fallback: plaskie linie typu "Imię Nazwisko – Title"
    if not staff:
        text = block.get_text("\n")
        lines = [normalize_space(l) for l in text.splitlines()]
        for line in lines:
            if "coach" not in line.lower():
                continue
            # np. "Scott Forbes – Head Coach"
            parts = re.split(r"[-–]|  ", line, maxsplit=1)
            if len(parts) >= 2:
                name = normalize_space(parts[0])
                title = normalize_space(parts[1])
                if name and title:
                    staff.append((name, title))

    return staff


def parse_staff_for_school(html: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Zwraca:
      - listę dictów dla Coach,
      - listę dictów dla SupportStaff.
    Każdy dict ma: fullName, role.
    """
    soup = BeautifulSoup(html, "html.parser")
    coaches: List[Dict] = []
    support: List[Dict] = []

    # 1) spróbuj znaleźć fajną tabelę staffu
    candidate_tables = []
    for table in soup.find_all("table"):
        header_text = normalize_space(table.get_text(" "))
        if "coach" in header_text.lower() or "title" in header_text.lower():
            candidate_tables.append(table)

    staff_pairs: List[Tuple[str, str]] = []
    for table in candidate_tables:
        staff_pairs.extend(parse_staff_from_table(table))

    # 2) jeśli tabel nie ma – spróbuj znaleźć blok "Coaching Staff"
    if not staff_pairs:
        text = soup.get_text(" ")
        if "Coaching Staff" in text or "Baseball Coaching Staff" in text:
            # weź fragmenty DOM zawierające słowa 'Coaching Staff'
            for tag in soup.find_all(string=re.compile("Coaching Staff", re.I)):
                block = tag.parent
                # rozszerz trochę w górę, bo często name+title jest w sąsiadach
                section = block.find_parent(["section", "div"]) or block.parent
                staff_pairs.extend(parse_staff_generic_block(section))

    # jeśli dalej pusto – spróbuj całej strony generically
    if not staff_pairs:
        staff_pairs.extend(parse_staff_generic_block(soup))

    # deduplikacja
    seen = set()
    clean_pairs: List[Tuple[str, str]] = []
    for name, title in staff_pairs:
        key = (name, title)
        if key not in seen:
            seen.add(key)
            clean_pairs.append(key)

    for name, title in clean_pairs:
        kind = classify_role(title)
        entry = {"fullName": name, "role": title}
        if kind == "coach":
            coaches.append(entry)
        else:
            support.append(entry)

    return coaches, support

from typing import List, Dict, Tuple


# --- 4) BUDOWANIE JSON POD KG ----------------------------------------------

def build_staff_json_for_school(cfg: SchoolConfig,
                                coaches: List[Dict],
                                support: List[Dict]) -> Dict:
    school_id = cfg.school_name.replace(" ", "_")
    team_id = f"{school_id}_baseball_{cfg.season_year}"

    return {
        "School": {
            "schoolId": school_id,
            "name": cfg.school_name,
            "conference": cfg.conference,
        },
        "Team": {
            "teamId": team_id,
            "teamName": f"{cfg.school_name} Baseball",
            "seasonYear": cfg.season_year,
        },
        "Coaches": [
            {
                "coachId": f"{team_id}_coach_{i+1}",
                "fullName": c["fullName"],
                "role": c["role"],
            }
            for i, c in enumerate(coaches)
        ],
        "SupportStaff": [
            {
                "staffId": f"{team_id}_staff_{i+1}",
                "fullName": s["fullName"],
                "role": s["role"],
            }
            for i, s in enumerate(support)
        ],
    }


# --- 5) MAIN ---------------------------------------------------------------

def main():
    all_data = []

    # utworzenie katalogu na surowe pliki staffu
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for cfg in SCHOOLS:
        print(f"\n=== {cfg.school_name} ===")
        base_url = cfg.staff_url or cfg.roster_url
        url = base_url
        if "roster" in base_url and "view=" not in base_url:
            url = ensure_view2(base_url)

        print(f"Fetching staff from: {url}")
        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch {url}: {e}")
            continue

        coaches, support = parse_staff_for_school(html)

        print(f"  Parsed {len(coaches)} coaches, {len(support)} support staff")
        for c in coaches[:3]:
            print(f"    Coach: {c['fullName']} – {c['role']}")
        for s in support[:2]:
            print(f"    Support: {s['fullName']} – {s['role']}")

        school_json = build_staff_json_for_school(cfg, coaches, support)
        all_data.append(school_json)

        safe_name = cfg.school_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name.lower()}_baseball_{cfg.season_year}_staff.json"
        out_path = os.path.join(OUTPUT_DIR, filename)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(school_json, f, indent=2, ensure_ascii=False)
        print(f"  Saved to {out_path}")



    with open("all_schools_staff.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("\nDone. Wrote all_schools_staff.json")


if __name__ == "__main__":
    main()
