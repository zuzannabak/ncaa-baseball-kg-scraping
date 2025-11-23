# NCAA Baseball Roster & Staff Scraper

Small scraping pipeline I built for a **Graph Databases** course project.  
The goal is to collect consistent roster and staff data for selected **NCAA Division I baseball programs**, clean it, and use the final JSON files as input for a **Neo4j knowledge graph** (Cypher + APOC).

The two main outputs used for Neo4j ingestion are:

- `all_schools_ontology_clean.json` – cleaned player + team ontology
- `all_schools_staff_clean.json` – cleaned staff data

---

## Repository structure

```text
final-scrape/
├── scraping/
│   ├── scrape_rosters.py            # scrape roster data for multiple schools
│   ├── scrape_staff.py              # scrape coaching/support staff data
│   └── parse_sidearm_view2_roster.py# helper for Sidearm "view=2" layouts
│
├── cleaning/
│   ├── clean_rosters.py             # normalize roster JSON → *_ontology_clean.json
│   └── clean_staff.py               # normalize staff JSON → *_staff_clean.json
│
├── raw_schools/                     # optional: per-school raw roster files
├── raw_staff/                       # optional: per-school raw staff files
│
├── all_schools_ontology.json        # combined raw player/roster data
├── all_schools_staff.json           # combined raw staff data
├── all_schools_ontology_clean.json  # final cleaned players/teams JSON
├── all_schools_staff_clean.json     # final cleaned staff JSON
└── .gitignore
```

---

## How to use it
1. Scrape rosters
```bash
python scraping/scrape_rosters.py
```
2. Scrape staff
```bash
python scraping/scrape_staff.py
```
3. Clean and normalize data
```bash
python cleaning/clean_rosters.py
python cleaning/clean_staff.py
```
After these steps, the JSON files:
* `all_schools_ontology_slean.json`
* `all_schools_staff_clean.json`
are ready to be loaded into Neo4j (e.g. with `apoc.load.json` + Cypher merge scripts).

---
## Next steps

In the main project I use these JSON files to build a multi-school NCAA baseball knowledge graph in Neo4j and run queries over conferences, positions, and roster composition.

