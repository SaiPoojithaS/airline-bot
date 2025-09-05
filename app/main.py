# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import httpx
import math, re
from typing import Tuple, Optional

# ============================================================
# Remote reference data (no local files)
# ============================================================
AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
COLS = ["id","name","city","country","IATA","ICAO","lat","lon","alt_ft","tz_offset","dst","tzdb","type","source"]
airports = pd.read_csv(AIRPORTS_URL, header=None, names=COLS)

# Lightweight preprocess for matching
airports["city_l"] = airports["city"].fillna("").str.lower()
airports["name_l"] = airports["name"].fillna("").str.lower()
iata_set = set(airports["IATA"].dropna().astype(str))

# ============================================================
# Helpers
# ============================================================
def find_location_from_message(msg_lower: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extract a location from the message:
      1) 3-letter IATA code as a whole word -> exact airport lat/lon
      2) else city/airport name substring (averaged lat/lon if multiple)
    Returns (lat, lon, label) or (None, None, None).
    """
    # --- IATA detection (whole-word only) ---
    msg_upper = msg_lower.upper()
    iata_hits = re.findall(r"\b[A-Z]{3}\b", msg_upper)

    # If the entire message is just 3 letters (e.g., "lax"), accept that too
    if not iata_hits and len(msg_upper.strip()) == 3:
        iata_hits = [msg_upper.strip()]

    for t in iata_hits:
        if t in iata_set:
            hits = airports.loc[
                airports["IATA"] == t,
                ["name","city","country","lat","lon","IATA"]
            ].dropna(subset=["lat","lon"])
            if not hits.empty:
                row = hits.iloc[0]
                label = f"{row['IATA']} - {row['name']} ({row['city']})"
                return float(row["lat"]), float(row["lon"]), label

    # Try city/airport name after cues like near/around/over/in
    m = re.search(r"(near|around|over|in)\s+([a-zA-Z .'-]+)", msg_lower)
    candidate = (m.group(2).strip() if m else msg_lower).lower()

    city_hits = airports.loc[
        airports["city_l"].str.contains(candidate, na=False),
        ["city","name","lat","lon","country","IATA"]
    ].dropna(subset=["lat","lon"])
    if not city_hits.empty:
        lat = float(city_hits["lat"].astype(float).mean())
        lon = float(city_hits["lon"].astype(float).mean())
        label = f"{city_hits.iloc[0]['city']} ({city_hits.iloc[0]['country']})"
        return lat, lon, label

    name_hits = airports.loc[
        airports["name_l"].str.contains(candidate, na=False),
        ["city","name","lat","lon","country","IATA"]
    ].dropna(subset=["lat","lon"])
    if not name_hits.empty:
        lat = float(name_hits["lat"].astype(float).mean())
        lon = float(name_hits["lon"].astype(float).mean())
        label = f"{name_hits.iloc[0]['name']} ({name_hits.iloc[0]['city']})"
        return lat, lon, label

    return None, None, None


def bbox_from_center(lat: float, lon: float, deg_pad: float = 1.5):
    """
    Simple lat/lon bounding box around a center.
    deg_pad ~ 1.5° ≈ 160km N/S (varies by latitude).
    """
    lamin = lat - deg_pad
    lamax = lat + deg_pad
    lon_pad = deg_pad / max(math.cos(math.radians(abs(lat))), 0.2)
    lomin = lon - lon_pad
    lomax = lon + lon_pad
    return {"lamin": round(lamin, 4), "lomin": round(lomin, 4), "lamax": round(lamax, 4), "lomax": round(lomax, 4)}


def query_opensky(params: dict):
    try:
        resp = httpx.get("https://opensky-network.org/api/states/all", params=params, timeout=30.0)
        if resp.status_code != 200:
            return None, f"OpenSky status {resp.status_code}"
        data = resp.json()
        return data.get("states") or [], None
    except Exception as e:
        return None, f"OpenSky error: {e}"


# --- FAQs (sync summaries; link to official sources) ---
def get_tsa_liquids_summary():
    url = "https://www.tsa.gov/travel/security-screening/whatcanibring/items/travel-size-toiletries"
    summary = ("TSA liquids rule (3-1-1): containers ≤ 3.4 oz / 100 mL; "
               "all containers fit in one quart-size transparent bag; one bag per passenger; "
               "place in bin for screening. Larger volumes → checked bag.")
    return summary, url


def get_faa_powerbank_summary():
    url = "https://www.faa.gov/hazmat/packsafe/lithium-batteries"
    summary = ("Power banks (lithium batteries): carry-on only (no checked). "
               "≤100 Wh allowed without airline approval; 100–160 Wh requires airline approval; "
               "protect terminals from short circuit.")
    return summary, url


# --- Airline baggage links router ---
def get_airline_baggage_link(text: str):
    t = text.lower()
    airlines = {
        # US
        "american": "https://www.aa.com/i18n/travel-info/baggage/baggage.jsp",
        "aa":       "https://www.aa.com/i18n/travel-info/baggage/baggage.jsp",
        "delta":    "https://www.delta.com/traveling-with-us/baggage",
        "dl":       "https://www.delta.com/traveling-with-us/baggage",
        "united":   "https://www.united.com/en/us/fly/travel/baggage.html",
        "ua":       "https://www.united.com/en/us/fly/travel/baggage.html",
        "southwest":"https://www.southwest.com/help/baggage",
        "wn":       "https://www.southwest.com/help/baggage",
        "alaska":   "https://www.alaskaair.com/travel-info/baggage/overview",
        "as":       "https://www.alaskaair.com/travel-info/baggage/overview",
        "jetblue":  "https://www.jetblue.com/help/baggage",
        "b6":       "https://www.jetblue.com/help/baggage",
        # Intl
        "air canada": "https://www.aircanada.com/ca/en/aco/home/plan/baggage.html",
        "ac":         "https://www.aircanada.com/ca/en/aco/home/plan/baggage.html",
        "british airways": "https://www.britishairways.com/en-us/information/baggage-essentials",
        "ba":              "https://www.britishairways.com/en-us/information/baggage-essentials",
        "lufthansa": "https://www.lufthansa.com/us/en/baggage-overview",
        "lh":        "https://www.lufthansa.com/us/en/baggage-overview",
        "emirates":  "https://www.emirates.com/us/english/before-you-fly/baggage/",
        "ek":        "https://www.emirates.com/us/english/before-you-fly/baggage/",
        "qatar":     "https://www.qatarairways.com/en-us/baggage/allowance.html",
        "qr":        "https://www.qatarairways.com/en-us/baggage/allowance.html",
        "singapore": "https://www.singaporeair.com/en_UK/us/travel-info/baggage/",
        "sq":        "https://www.singaporeair.com/en_UK/us/travel-info/baggage/",
    }
    multi = ["air canada", "british airways"]
    for m in multi:
        if m in t:
            return m.title(), airlines[m]
    name_map = {
        "aa":"American Airlines","dl":"Delta Air Lines","ua":"United Airlines","wn":"Southwest Airlines",
        "as":"Alaska Airlines","b6":"JetBlue","ac":"Air Canada","ba":"British Airways","lh":"Lufthansa",
        "ek":"Emirates","qr":"Qatar Airways","sq":"Singapore Airlines"
    }
    for key, url in airlines.items():
        if key in multi:
            continue
        if re.search(rf"\b{re.escape(key)}\b", t):
            return name_map.get(key, key.title()), url
    return None, None


# --- Power bank calculator (mAh → Wh) ---
def powerbank_wh_from_text(text: str) -> Optional[Tuple[float, float]]:
    """
    Extract (mAh, V) or Wh from text.
    - If "Wh" present: return (Wh, None)
    - Else if "mAh" present: need voltage (look for 'V' or assume 3.7V)
    Returns (Wh, voltage_used) or None if not found.
    """
    t = text.lower().replace(",", " ")
    # Direct Wh
    m_wh = re.search(r"(\d+(\.\d+)?)\s*wh\b", t)
    if m_wh:
        return float(m_wh.group(1)), None
    # mAh (+ optional voltage)
    m_mah = re.search(r"(\d+(\.\d+)?)\s*mah\b", t)
    if m_mah:
        mah = float(m_mah.group(1))
        m_v = re.search(r"(\d+(\.\d+)?)\s*v\b", t)
        v = float(m_v.group(1)) if m_v else 3.7  # typical Li-ion nominal voltage
        wh = (mah/1000.0) * v
        return wh, v
    return None


def classify_wh(wh: float):
    """FAA guidance buckets."""
    if wh <= 100:
        return "Allowed in carry-on without airline approval (no checked baggage)."
    elif wh <= 160:
        return "Carry-on allowed with airline approval (no checked baggage)."
    else:
        return "Not allowed for passenger aircraft (exceeds 160 Wh)."


# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(title="Airline Chatbot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False
)

class Query(BaseModel):
    message: str


@app.get("/")
def root():
    return {"msg": "Airline Chatbot API. Use POST /chat or open /docs for Swagger UI."}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
async def chat(q: Query):
    user_msg = q.message.strip()
    user_l   = user_msg.lower()

    # ---------- Airport lookup ----------
    iata_hits = re.findall(r"\b[A-Z]{3}\b", user_msg.upper())
    if not iata_hits and len(user_msg.strip()) == 3:
        iata_hits = [user_msg.strip().upper()]

    for code in iata_hits:
        if code in iata_set:
            r = airports.loc[airports["IATA"] == code, ["name","city","country","IATA","ICAO"]]
            if not r.empty:
                row = r.iloc[0]
                return {"answer": f"{row['IATA']} = {row['name']} in {row['city']}, {row['country']} (ICAO {row['ICAO']})."}

    by_city = airports.loc[airports["city_l"].str.contains(user_l, na=False), ["name","city","country","IATA","ICAO"]]
    if not by_city.empty:
        row = by_city.iloc[0]
        return {"answer": f"Airport in {row['city']}: {row['name']} (IATA {row['IATA']}, ICAO {row['ICAO']})."}

    by_name = airports.loc[airports["name_l"].str.contains(user_l, na=False), ["name","city","country","IATA","ICAO"]]
    if not by_name.empty:
        row = by_name.iloc[0]
        return {"answer": f"{row['name']} is in {row['city']}, {row['country']} (IATA {row['IATA']}, ICAO {row['ICAO']})."}

    # ---------- Live aircraft near a place ----------
    if any(k in user_l for k in ["flight", "flights", "aircraft", "planes", "plane", "over", "near", "around", "in"]):
        lat, lon, label = find_location_from_message(user_l)
        if lat is not None and lon is not None:
            params = bbox_from_center(lat, lon, deg_pad=1.5)
            states, err = query_opensky(params)
            if err:
                return {"answer": f"Could not fetch live data ({err}). Try again shortly."}
            if states:
                examples = []
                for s in states[:5]:
                    callsign = (s[1] or "").strip() or "unknown"
                    alt_m = s[13] if isinstance(s[13], (int, float)) else 0
                    examples.append(f"{callsign} at {round(alt_m)} m")
                return {"answer": f"Found {len(states)} aircraft near {label}. Examples: {', '.join(examples)}."}
            else:
                return {"answer": f"No live aircraft found near {label} right now."}
        # they asked about flights but we couldn't parse a place; fall through

    # ---------- FAQs: liquids & batteries ----------
    if any(k in user_l for k in ["liquid", "toiletries", "3-1-1", "3 1 1", "100ml", "100 ml"]):
        info, src = get_tsa_liquids_summary()
        return {"answer": info, "source": src}

    # power bank calculator if they give specs
    if any(k in user_l for k in ["power bank", "powerbank", "battery", "lithium", "mah", "wh"]):
        calc = powerbank_wh_from_text(user_l)
        if calc:
            wh, v = calc
            verdict = classify_wh(wh)
            v_txt = "" if v is None else f" using {v} V,"
            return {
                "answer": f"Estimated capacity ≈ {wh:.1f} Wh{v_txt} which falls under: {verdict}",
                "source": "https://www.faa.gov/hazmat/packsafe/lithium-batteries"
            }
        info, src = get_faa_powerbank_summary()
        return {"answer": info, "source": src}

    # ---------- Airline baggage policy links ----------
    if any(k in user_l for k in ["baggage", "luggage", "checked bag", "carry-on", "carry on", "baggage allowance", "bag fee"]):
        name, link = get_airline_baggage_link(user_l)
        if link:
            return {"answer": f"Here’s the official baggage policy for {name}:", "source": link}
        return {"answer": "Tell me the airline (e.g., 'baggage for United', 'AA baggage allowance', 'Delta carry-on size') and I’ll fetch the official policy link."}

    # ---------- Fallback ----------
    return {
        "answer": ("I can help with airport codes/names, live aircraft near a place, liquids/battery rules, "
                   "and airline baggage links. Try: "
                   "'planes over LAX', 'Any flights near New York?', "
                   "'what’s the liquids rule?', 'can I carry 20000 mAh power bank at 5V?', "
                   "'United baggage allowance'.")
    }