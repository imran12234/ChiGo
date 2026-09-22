# ChiGo – AI-Powered Trip Planning Web App

**ChiGo** is a full-stack AI-powered trip planning application that generates personalized, multi-day Chicago itineraries using structured user preferences, constrained LLM outputs, and real-world location data.

🔗 **Live Demo:** https://chi-go-v2.onrender.com

---

## Overview

ChiGo helps users plan trips by combining structured survey inputs with controlled AI generation and external mapping services. Instead of free-form text generation, the system enforces deterministic structure, validates outputs, and enriches recommendations with real-world data.

The project emphasizes **backend system design, responsible LLM integration, and production deployment**.

---

## Key Features

- Personalized multi-day itinerary generation using OpenAI GPT-4o-mini  
- Structured survey-based preference collection (cuisine, activity level, budget, neighborhoods)  
- Schema-guided AI prompting with enforced JSON output  
- Activity enrichment with real coordinates, addresses, photos, and ratings via Google Places API  
- Interactive activity-swapping system with AI-generated alternatives  
- Transit time calculation between itinerary stops using Google Routes API with Haversine fallback  
- Persistent storage of trips and activities with session-aware updates  

---

## System Architecture

### Backend
- Django-based MVC architecture  
- ORM-backed relational data models  
- Form-driven survey validation and normalization  
- Business logic layer for itinerary orchestration and updates  

### AI Layer
- OpenAI GPT-4o-mini for itinerary generation  
- Prompt pipeline enforcing:
  - Exact number of days  
  - Day-by-day activity structure  
  - Distance and neighborhood constraints  
- Separation of AI logic from application logic to prevent hallucinations  

### External Services
- **Google Places API** for validating and enriching activities  
- **Google Routes API** for walk/drive transit time estimation  
- Haversine distance fallback for geospatial robustness  

### Data Layer
- PostgreSQL for persistent storage  
- Normalized models for itineraries, activities, and preferences  

---

## Example Workflow

1. User completes a structured trip survey (dates, cuisine, activity level, budget, neighborhood)  
2. Backend validates and normalizes survey inputs  
3. AI prompt pipeline generates a constrained, structured itinerary  
4. Activities are enriched with real-world data and coordinates  
5. Transit times between consecutive stops are calculated  
6. Itinerary is stored and rendered in the user dashboard  
7. Users can swap individual activities with AI-generated alternatives in real time  

---

## Tech Stack

- **Language:** Python  
- **Framework:** Django  
- **Database:** PostgreSQL  
- **AI:** OpenAI GPT-4o-mini  
- **APIs:** Google Places API, Google Routes API  
- **Deployment:** Docker, Render, Gunicorn  
- **Other:** Django ORM, WhiteNoise, Session Management  

---

## Deployment

ChiGo is containerized with Docker and deployed to Render using:

- Gunicorn application server  
- Managed PostgreSQL database  
- WhiteNoise for static file serving  

---

## Google Places and itinerary maps

Place enrichment uses **Places API (New)** from the Django server (`PLACES_API_KEY`).
The itinerary builder and summary use **Maps JavaScript API** to display those
coordinates, with markers and a separate connecting line for each day.

Set these environment variables locally in the ignored `.env`, and separately
in your deployment environment:

```dotenv
PLACES_API_KEY=your_server_places_key
GOOGLE_MAPS_BROWSER_KEY=your_website_restricted_maps_key
GOOGLE_MAPS_MAP_ID=your_map_id
```

Enable Places API (New) and Maps JavaScript API in the owning Google Cloud
projects, with active billing. Use a separate browser key restricted to your
website URLs and Maps JavaScript API. The server Places key is never used as a
browser-key fallback. `DEMO_MAP_ID` is the development default; configure your own
map ID for deployment. Without a browser key, the page provides a Google Maps
link; failed photo requests display “Photo unavailable.”

Existing itineraries retain their saved coordinates and photo references;
changing keys does not re-enrich them. Generate a new itinerary after fixing
Places access. Google HTTP 403 responses still require resolving account/API/key
permissions; changing the map renderer does not remove that requirement.

The evidence under `metrics/` measures the **original application version** before
these integration changes. Its original test counts and timings must not be
presented as measurements of this updated code.
