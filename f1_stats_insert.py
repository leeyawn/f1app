import json
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase Headers
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Load JSON Data
with open("F1_Standings_2025.json", "r", encoding="utf-8") as file:
    json_data = json.load(file)

# Ensure JSON is structured correctly
if not isinstance(json_data, dict):
    raise ValueError("Expected JSON to be a dictionary, but got:", type(json_data))

# Debug: Print available keys to determine structure
print("JSON Keys:", json_data.keys())

# Extract the standings data
if "standings" in json_data and "entries" in json_data["standings"]:
    standings = json_data["standings"]["entries"]
else:
    raise ValueError("Could not find standings data in JSON. Available keys:", json_data.keys())

# Ensure standings is a list
if not isinstance(standings, list):
    raise ValueError("Expected standings to be a list, but got:", type(standings))

# Debug: Print first few entries to confirm structure
print("First 2 entries:", standings[:2])

# Insert Drivers
def insert_drivers(drivers):
    url = f"{SUPABASE_URL}/rest/v1/drivers"
    for driver in drivers:
        driver_data = {
            "driver_id": driver["athlete"]["id"],
            "driver_name": driver["athlete"]["displayName"],
            "abbreviation": driver["athlete"]["abbreviation"],
            "nationality": driver["athlete"]["flag"]["alt"],
            "href": driver["athlete"]["flag"]["href"],
            "team": driver.get("team", "Unknown")  # Adjust if team data is available in JSON
        }
        # Use UPSERT to avoid duplicate key errors
        response = requests.post(url, json=driver_data, headers={**HEADERS, "Prefer": "resolution=merge-duplicates"})
        if response.status_code != 201:
            print(f"Failed to insert driver: {driver_data}, Error: {response.text}")
        else:
            print(f"Driver Inserted/Updated: {driver_data['driver_name']}")

# Insert Races
def insert_races(races):
    url = f"{SUPABASE_URL}/rest/v1/races"
    for race in races:
        race_date = race.get("race_date")
        # Ensure race_date is a valid ISO 8601 datetime string
        if race_date and race_date != "Unknown":
            race_date = f"{race_date}T00:00:00Z"  # Append time and timezone if missing
        else:
            race_date = "1970-01-01T00:00:00Z"  # Default value

        race_data = {
            "race_id": race["name"],
            "race_name": race["displayName"],
            "race_date": race_date,
            "location": race.get("location", "Unknown")
        }
        # Use UPSERT to avoid duplicate key errors
        response = requests.post(url, json=race_data, headers={**HEADERS, "Prefer": "resolution=merge-duplicates"})
        if response.status_code != 201:
            print(f"Failed to insert race: {race_data}, Error: {response.text}")
        else:
            print(f"Race Inserted/Updated: {race_data['race_name']}")

# Insert Standings
def insert_standings(standings):
    url = f"{SUPABASE_URL}/rest/v1/f1_standings"
    for entry in standings:
        race_name = next(
            (stat["displayName"] for stat in entry["stats"] if stat["name"] == "rank"), 
            "Unknown"
        )
        race_date = "1970-01-01T00:00:00Z"  # Default value
        team = entry.get("team", "Unknown")  # Default team if missing

        standings_data = {
            "race_id": entry["stats"][0]["name"],  # Adjust based on JSON structure
            "race_name": race_name,
            "race_date": race_date,
            "driver_id": entry["athlete"]["id"],
            "driver_name": entry["athlete"]["displayName"],  # Include driver_name
            "team": team,  # Include team
            "position": entry["stats"][0]["value"],  # Adjust based on JSON structure
            "points": entry["stats"][1]["value"]  # Adjust based on JSON structure
        }
        response = requests.post(url, json=standings_data, headers=HEADERS)
        if response.status_code != 201:
            print(f"Failed to insert standings: {standings_data}, Error: {response.text}")
        else:
            print(f"Standings Inserted for Driver ID: {standings_data['driver_id']}")

# Extract Unique Drivers & Races
unique_drivers = {entry["athlete"]["id"]: entry for entry in standings if isinstance(entry, dict)}.values()
unique_races = {stat["name"]: stat for entry in standings for stat in entry["stats"] if stat["name"] not in ["rank", "championshipPts"]}.values()

# Execute Inserts
insert_drivers(unique_drivers)
insert_races(unique_races)
insert_standings(standings)

print("Data inserted successfully!")