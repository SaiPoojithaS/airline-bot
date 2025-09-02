import pandas as pd
import httpx

# ------------------------------
# 1) OpenFlights Airports Dataset (CSV)
# ------------------------------
airports_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"

cols = ["id","name","city","country","IATA","ICAO","lat","lon","alt_ft","tz_offset","dst","tzdb","type","source"]
airports = pd.read_csv(airports_url, header=None, names=cols)

print("✅ Airports loaded:", len(airports))
print(airports.query("IATA == 'DFW'")[["name","city","country","IATA","ICAO"]].head())

# ------------------------------
# 2) OpenSky API - Live Aircraft States (JSON)
# Dallas–Fort Worth bounding box
# ------------------------------
params = {"lamin": 31.0, "lomin": -100.0, "lamax": 35.5, "lomax": -94.0}
resp = httpx.get("https://opensky-network.org/api/states/all", params=params, timeout=30.0)

print("✅ OpenSky status code:", resp.status_code)

if resp.status_code == 200:
    data = resp.json()
    print("Keys:", list(data.keys()))
    if data.get("states"):
        print("Sample state vector length:", len(data["states"][0]))
        print("First aircraft:", data["states"][0])
    else:
        print("No live aircraft found in this box at this moment.")