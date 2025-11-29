# app.py
import streamlit as st
from neo4j import GraphDatabase
from neo4j_config import get_driver

# -------------------------------------------------------------------
# Neo4j helper
# -------------------------------------------------------------------
driver = get_driver()

def run_query(query: str, params: dict | None = None):
    """Run a Cypher query and return a list of dicts (record.data())."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]

# -------------------------------------------------------------------
# Streamlit page setup
# -------------------------------------------------------------------
st.set_page_config(page_title="NCAA Baseball KG", layout="wide")
st.title("NCAA Division I Baseball Knowledge Graph")

# -------------------------------------------------------------------
# Sidebar: conference + team selection
# -------------------------------------------------------------------
conferences = run_query(
    """
    MATCH (c:Conference)
    RETURN c.conferenceId AS id, c.conferenceName AS name
    ORDER BY name
    """
)

if not conferences:
    st.error("No conferences found in the database.")
    st.stop()

conf_names = {c["name"]: c["id"] for c in conferences}

selected_conf_name = st.sidebar.selectbox(
    "Conference",
    list(conf_names.keys()),
)

selected_conf_id = conf_names[selected_conf_name]

# Teams in the selected conference
teams = run_query(
    """
    MATCH (s:School)-[:MEMBER_OF]->(c:Conference {conferenceId: $cid})
    MATCH (s)-[:HAS_TEAM]->(t:Team)
    RETURN t.teamId AS id, t.teamName AS name
    ORDER BY name
    """,
    {"cid": selected_conf_id},
)

if not teams:
    st.warning("No teams found for this conference.")
    st.stop()

team_names = {t["name"]: t["id"] for t in teams}

selected_team_name = st.sidebar.selectbox(
    "Team",
    list(team_names.keys()),
)

selected_team_id = team_names[selected_team_name]

# -------------------------------------------------------------------
# Tabs for different views
# -------------------------------------------------------------------
tab_overview, tab_roster, tab_staff, tab_explorer = st.tabs(
    ["Overview", "Roster", "Staff", "Explorer"]
)

# -------------------------------------------------------------------
# TAB 1: Overview
# -------------------------------------------------------------------
with tab_overview:
    st.subheader("Team overview")

    # Basic info about school + conference + team
    info = run_query(
        """
        MATCH (s:School)-[:HAS_TEAM]->(t:Team {teamId: $tid})
        MATCH (s)-[:MEMBER_OF]->(c:Conference)
        OPTIONAL MATCH (t)-[:PARTICIPATES_IN]->(se:Season)
        RETURN s.name AS schoolName,
               c.conferenceName AS conferenceName,
               collect(DISTINCT se.seasonYear) AS seasons
        """,
        {"tid": selected_team_id},
    )

    if info:
        row = info[0]
        st.markdown(
            f"""
            **School:** {row.get("schoolName", "N/A")}  
            **Conference:** {row.get("conferenceName", "N/A")}  
            **Seasons in graph:** {", ".join(map(str, row["seasons"])) if row["seasons"] else "N/A"}
            """
        )

    # Simple counts: players, coaches, staff
    counts = run_query(
        """
        MATCH (t:Team {teamId: $tid})
        OPTIONAL MATCH (p:Player)-[:PLAYS_FOR]->(t)
        OPTIONAL MATCH (c:Coach)-[:COACHES]->(t)
        OPTIONAL MATCH (s:SupportStaff)-[:WORKS_FOR]->(t)
        RETURN count(DISTINCT p) AS players,
               count(DISTINCT c) AS coaches,
               count(DISTINCT s) AS staff
        """,
        {"tid": selected_team_id},
    )[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Players", counts["players"])
    c2.metric("Coaches", counts["coaches"])
    c3.metric("Support staff", counts["staff"])

    # Optional: quick breakdown by class year
    st.markdown("### Player class year distribution")
    class_counts = run_query(
        """
        MATCH (p:Player)-[:PLAYS_FOR]->(t:Team {teamId: $tid})
        RETURN p.classYear AS classYear, count(*) AS cnt
        ORDER BY cnt DESC
        """,
        {"tid": selected_team_id},
    )
    if class_counts:
        st.bar_chart(
            {row["classYear"]: row["cnt"] for row in class_counts}
        )
    else:
        st.info("No players found for class-year distribution.")

# -------------------------------------------------------------------
# TAB 2: Roster
# -------------------------------------------------------------------
with tab_roster:
    st.subheader(f"Roster – {selected_team_name}")

    players = run_query(
        """
        MATCH (p:Player)-[:PLAYS_FOR]->(t:Team {teamId: $tid})
        RETURN p.fullName   AS name,
               p.classYear  AS classYear,
               p.position   AS position,
               p.height     AS height,
               p.weight     AS weight,
               p.hometown   AS hometown,
               p.lastSchool AS lastSchool
        ORDER BY name
        """,
        {"tid": selected_team_id},
    )

    st.dataframe(players, use_container_width=True)

# -------------------------------------------------------------------
# TAB 3: Staff (coaches + support staff)
# -------------------------------------------------------------------
with tab_staff:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Coaches")
        coaches = run_query(
            """
            MATCH (c:Coach)-[:COACHES]->(t:Team {teamId: $tid})
            RETURN c.fullName AS name,
                   c.role     AS role
            ORDER BY role, name
            """,
            {"tid": selected_team_id},
        )
        st.dataframe(coaches, use_container_width=True)

    with col2:
        st.subheader("Support staff")
        staff = run_query(
            """
            MATCH (s:SupportStaff)-[:WORKS_FOR]->(t:Team {teamId: $tid})
            RETURN s.fullName AS name,
                   s.role     AS role
            ORDER BY role, name
            """,
            {"tid": selected_team_id},
        )
        st.dataframe(staff, use_container_width=True)

# -------------------------------------------------------------------
# TAB 4: Simple Cypher explorer (for you / TA)
# -------------------------------------------------------------------
with tab_explorer:
    st.subheader("Cypher explorer (read-only)")

    default_query = f"""
// Example: small ego-graph around the selected team
MATCH (t:Team {{teamId: '{selected_team_id}'}})
OPTIONAL MATCH (t)<-[:PLAYS_FOR]-(p:Player)
OPTIONAL MATCH (t)<-[:COACHES]-(c:Coach)
OPTIONAL MATCH (t)<-[:WORKS_FOR]-(s:SupportStaff)
RETURN t.teamName AS team,
       collect(DISTINCT p.fullName) AS players,
       collect(DISTINCT c.fullName) AS coaches,
       collect(DISTINCT s.fullName) AS staff
    """.strip()

    user_query = st.text_area(
        "Cypher query (read-only, no writes)",
        value=default_query,
        height=200,
    )

    if st.button("Run query"):
        try:
            data = run_query(user_query)
            st.write(data)
        except Exception as e:
            st.error(f"Query failed: {e}")
