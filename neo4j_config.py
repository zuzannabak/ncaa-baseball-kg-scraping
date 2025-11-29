# neo4j_config.py
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()  # wczyta .env jeśli istnieje

URI = os.getenv("NEO4J_URI", "neo4j+s://c8d283cc.databases.neo4j.io")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def get_driver():
    return driver
