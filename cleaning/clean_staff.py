import json
import pathlib

# --- konfiguracja ---
RAW_DIR = pathlib.Path("raw_staff")   # katalog z plikami *_staff.json
ALL_FILE = pathlib.Path("all_schools_staff.json")  # zbiorczy plik
OUT_DIR = pathlib.Path("clean_staff")
OUT_DIR.mkdir(exist_ok=True)


def clean_str(s):
    """Przytnij spacje i znormalizuj whitespace w środku."""
    if not isinstance(s, str):
        return s
    # "  Director   of  Ops  " -> "Director of Ops"
    return " ".join(s.split()).strip()


def clean_entry(entry):
    """Oczyść jeden obiekt (jedna szkoła) w formacie School/Team/Coaches/SupportStaff."""
    school = entry.get("School", {})
    team = entry.get("Team", {})

    for key in ("schoolId", "name", "conference"):
        if key in school:
            school[key] = clean_str(school[key])

    for key in ("teamId", "teamName", "seasonYear"):
        if key in team:
            team[key] = clean_str(team[key])

    cleaned_coaches = []
    for c in entry.get("Coaches", []):
        c["coachId"] = clean_str(c.get("coachId", ""))
        c["fullName"] = clean_str(c.get("fullName", ""))
        c["role"] = clean_str(c.get("role", ""))
        # wyrzuć zupełnie puste rekordy
        if c["fullName"]:
            cleaned_coaches.append(c)

    cleaned_staff = []
    for s in entry.get("SupportStaff", []):
        s["staffId"] = clean_str(s.get("staffId", ""))
        s["fullName"] = clean_str(s.get("fullName", ""))
        s["role"] = clean_str(s.get("role", ""))
        if s["fullName"]:
            cleaned_staff.append(s)

    entry["Coaches"] = cleaned_coaches
    entry["SupportStaff"] = cleaned_staff
    entry["School"] = school
    entry["Team"] = team
    return entry


def load_from_raw_dir():
    """Przeczytaj wszystkie pliki JSON z raw_staff/ (jeśli tak chcesz)."""
    all_entries = []
    for path in RAW_DIR.glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # pojedynczy obiekt lub lista
        if isinstance(data, list):
            entries = data
        else:
            entries = [data]

        all_entries.extend(entries)
    return all_entries


def load_from_all_file():
    """Przeczytaj zbiorczy all_schools_staff.json."""
    with open(ALL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # zakładamy listę
    return data


def main(use_raw_dir=False):
    """
    use_raw_dir = False  -> czytaj tylko all_schools_staff.json
    use_raw_dir = True   -> czytaj wszystkie pliki z raw_staff/
    """
    if use_raw_dir:
        entries = load_from_raw_dir()
    else:
        entries = load_from_all_file()

    cleaned_all = []

    for entry in entries:
        cleaned = clean_entry(entry)
        cleaned_all.append(cleaned)

        school_id = cleaned.get("School", {}).get("schoolId", "unknown_school")
        out_path = OUT_DIR / f"{school_id}_staff_clean.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

    # zbiorczy, oczyszczony JSON
    out_all = "all_schools_staff_clean.json"
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(cleaned_all, f, ensure_ascii=False, indent=2)

    print(f"Zapisano {len(cleaned_all)} szkół do katalogu {OUT_DIR}/")
    print(f"Zbiorczy plik: {out_all}")


if __name__ == "__main__":
    # jeśli chcesz czytać z katalogu raw_staff, zmień na True
    main(use_raw_dir=False)
