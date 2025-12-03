# parser_sidearm_view2.py
from bs4 import BeautifulSoup

def norm(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.split())

def pick_best_roster_table(soup: BeautifulSoup):
    """
    Szukamy tabeli, której nagłówki wyglądają jak roster:
    coś z 'jersey', 'name', 'pos', 'ht', 'wt', 'yr', 'hometown' itd.
    """
    best_table = None
    best_score = -1

    for table in soup.find_all("table"):
        # spróbuj znaleźć pierwszy wiersz nagłówka
        header_row = None

        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")

        if not header_row:
            # czasem nagłówki są w pierwszym <tr> w <tbody> lub bez thead
            header_row = table.find("tr")

        if not header_row:
            continue

        headers = []
        for th in header_row.find_all(["th", "td"]):
            headers.append(norm(th.get_text()))

        if not headers:
            continue

        # score = ile słów-kluczy z rosteru występuje w nagłówkach
        score = 0
        joined = " ".join(h.lower() for h in headers)
        for kw in ["jersey", "#", "name", "pos", "position", "ht", "height", "wt", "weight", "yr", "class", "hometown", "high school", "previous school"]:
            if kw in joined:
                score += 1

        if score > best_score:
            best_score = score
            best_table = table

    return best_table

def parse_home_and_school(text: str):
    """
    Próbujemy z pola typu:
       'Katy, Texas / Obra D. Tompkins'
       'Lexington, Ky. / Kentucky'
       'Whittier, Calif. Los Altos HS'
    wyciągnąć (hometown, lastSchool).
    """
    text = norm(text)
    if not text:
        return "", ""

    # jeśli jest '/', traktujemy lewą stronę jako hometown, prawą jako school
    if "/" in text:
        left, right = text.split("/", 1)
        return left.strip(), right.strip()

    # inaczej: rozbijamy po przecinku i kropce od stanu
    if "," not in text:
        # nietypowo – wszystko jako hometown
        return text, ""

    city, tail = text.split(",", 1)
    tail = tail.strip()
    tail_tokens = tail.split()
    if not tail_tokens:
        return text, ""

    # znajdź token ze skrótem stanu (kończy się kropką, np. 'Ky.', 'Calif.', 'Ind.')
    state_end_idx = None
    for i, tok in enumerate(tail_tokens):
        if tok.endswith("."):
            state_end_idx = i
            break

    if state_end_idx is None:
        # traktujemy wszystko jako hometown
        return text, ""

    hometown = city.strip() + ", " + " ".join(tail_tokens[:state_end_idx + 1])
    last_school = " ".join(tail_tokens[state_end_idx + 1:]).strip()
    return hometown, last_school

def parse_sidearm_roster_view2(html: str):
    """
    Parser tabelowy dla layoutu view=2 (Fullerton, UCSB, Evansville, Wichita).
    Zakładamy, że jest tabela z nagłówkami w stylu:
      Jersey | Name | Pos. | Ht. | Wt. | Yr. | Hometown / High School
    """
    soup = BeautifulSoup(html, "html.parser")
    table = pick_best_roster_table(soup)
    if table is None:
        return []

    # zmapuj nagłówki na indeksy kolumn
    header_row = None
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
    if not header_row:
        header_row = table.find("tr")
    if not header_row:
        return []

    headers = [norm(th.get_text()).lower() for th in header_row.find_all(["th", "td"])]

    jersey_idx = name_idx = pos_idx = ht_idx = wt_idx = yr_idx = home_idx = school_idx = bt_idx = None

    for idx, h in enumerate(headers):
            if "jersey" in h or h == "#" or h.startswith("no."):
                jersey_idx = idx
            elif "name" in h:
                name_idx = idx
            elif "pos" in h and "opponent" not in h:
                pos_idx = idx
            elif h.startswith("ht") or "height" in h:
                ht_idx = idx
            elif h.startswith("wt") or "weight" in h:
                wt_idx = idx
            elif "yr" in h or "year" in h or "class" in h or h.startswith("cl"):
                yr_idx = idx
            elif "b/t" in h or "bats" in h or "throws" in h:
                bt_idx = idx          # 👈 NOWA KOLUMNA
            elif "hometown" in h and "school" in h:
                home_idx = idx
            elif "hometown" in h:
                home_idx = idx
            elif "high school" in h or "previous school" in h:
                school_idx = idx



    players = []
    # wiersze danych – wszystko po nagłówku
    rows = []
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
    else:
        # fallback: wszystkie tr po pierwszym
        rows = table.find_all("tr")[1:]

    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        texts = [norm(c.get_text()) for c in cells]

        def get(idx):
            if idx is None:
                return ""
            if idx < 0 or idx >= len(texts):
                return ""
            return texts[idx]

        jersey = get(jersey_idx)
        name = get(name_idx)
        pos = get(pos_idx)
        height = get(ht_idx)
        weight = get(wt_idx)
        # jeśli waga jest samą liczbą, dopisujemy ' lbs'
        if weight and weight.isdigit():
            weight = weight + " lbs"
        class_year = get(yr_idx)
        bt = get(bt_idx)


        hometown = ""
        last_school = ""

        # jeżeli mamy osobne kolumny hometown + school
        if home_idx is not None and school_idx is not None:
            hometown = get(home_idx)
            last_school = get(school_idx)
        else:
            # pojedyncza kolumna 'Hometown/High School' albo podobna
            combined = get(home_idx)
            hometown, last_school = parse_home_and_school(combined)

        # jeżeli nie mamy imienia albo numeru, nie dodajemy
        if not name:
            continue

        players.append(
            {
                "full_name": name,
                "jersey": jersey,
                "position": pos,
                "class_year": class_year,
                "height": height,
                "weight": weight,
                "hometown": hometown,
                "last_school": last_school,
                "bats_throws": bt,   # 👈 DODANE
            }
        )

    # deduplikacja
    uniq = {}
    for p in players:
        key = (p["full_name"], p["jersey"])
        if key not in uniq:
            uniq[key] = p

    return list(uniq.values())
