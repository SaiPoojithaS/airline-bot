# SkyBuddy ✈️ — Airline Chatbot

SkyBuddy is a lightweight chatbot that helps travelers get quick answers about **airports, baggage rules, TSA liquids, FAA battery policies, and live aircraft nearby**.  
It combines a **FastAPI backend** (deployed on Render) with a **static frontend** (HTML/CSS/JS on GitHub Pages).

---

## 🚀 Live Demo
Frontend: [SkyBuddy on GitHub Pages](https://saipoojithas.github.io/airline-bot-ui/)  
Backend: [Render API](https://airline-bot-ry5f.onrender.com/)

---

## ✨ Features
- 🔎 **Airport Lookup** → Enter IATA codes or city names (e.g., “DFW”, “airport in Tokyo”).  
- 🛫 **Live Flights Nearby** → Get live aircraft near a city or airport via OpenSky API.  
- 🧴 **TSA Liquids Rule** → Quick 3-1-1 summary with official TSA link.  
- 🔋 **Battery Rules** → Enter mAh/Wh to see FAA classification with source.  
- 🎒 **Airline Baggage Policies** → Direct links to official airline sites (AA, UA, Delta, BA, etc.).  

---

## 🏗️ Architecture
- **Frontend:** Static web app (HTML/CSS/JS), hosted on **GitHub Pages**.  
- **Backend:** REST API built with **FastAPI**, deployed on **Render**.  
- **Data Sources:**  
  - OpenFlights dataset (airports metadata)  
  - OpenSky API (live flights)  
  - TSA & FAA websites (policies)  
  - Official airline websites (baggage rules)  

---

## ⚙️ Tech Stack
- **Backend:** Python, FastAPI, httpx, pandas, Pydantic, Uvicorn  
- **Frontend:** HTML5, CSS3, Vanilla JS  
- **Hosting:** Render (backend), GitHub Pages (frontend)  
- **Data:** OpenFlights, OpenSky Network, TSA, FAA, airline websites  

---

## 📂 Project Structure
