"""
main.py  -  the BACKEND (FastAPI) of the astronaut health app.

What this file does (in simple words):
  It opens "doors" (links) that the React screens can knock on.
  Each door uses a helper from database.py to read or save data,
  then sends the answer back to the screen as JSON.

How to run it:
  1. pip install fastapi uvicorn
  2. uvicorn main:app --reload
  3. Open http://127.0.0.1:8000/docs  to see and test every door.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db

app = FastAPI(title="Astronaut Health API")

# Let the React app (running on the same laptop) talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# The shapes of data the screens send to us
# ---------------------------------------------------------------------------
class LoginIn(BaseModel):
    username: str
    pin: str


class CheckInIn(BaseModel):
    astronaut_id: str
    day: int
    sleep_hours: float
    heart_rate: int
    mood: int
    stress: int
    miss_family: int
    feeling: str
    reaction_ms: int
    radiation_msv: float
    exercise_min: int
    co2_ppm: int


class PrivacyIn(BaseModel):
    astronaut_id: str
    share_mood: int
    share_sleep: int


class MessageIn(BaseModel):
    astronaut_id: str
    message: str


# ---------------------------------------------------------------------------
# The doors (links)
# ---------------------------------------------------------------------------

# Login screen
@app.post("/login")
def login(data: LoginIn):
    astronaut = db.login(data.username, data.pin)
    if astronaut is None:
        raise HTTPException(status_code=401, detail="Wrong username or code")
    return astronaut


# Check-in game: save one new day
@app.post("/checkin")
def checkin(data: CheckInIn):
    db.save_reading(**data.model_dump())
    return {"saved": True}


# History charts + live simulation: all days (or some days)
@app.get("/readings/{astronaut_id}")
def readings(astronaut_id: str, from_day: int = 1, to_day: int = 10_000):
    return db.get_readings(astronaut_id, from_day, to_day)


# Dashboard + human body: the 5 dial scores for one day
@app.get("/dials/{astronaut_id}/{day}")
def dials(astronaut_id: str, day: int):
    scores = db.get_dial_scores(astronaut_id, day)
    if scores is None:
        raise HTTPException(status_code=404, detail="No scores for this day yet")
    return scores


# Guidance + reminders: action cards not done yet
@app.get("/alerts/{astronaut_id}")
def alerts(astronaut_id: str):
    return db.get_open_alerts(astronaut_id)


# Astronaut ticks a card as done
@app.post("/alerts/{alert_id}/done")
def alert_done(alert_id: int):
    db.mark_alert_done(alert_id)
    return {"done": True}


# Mission health report
@app.get("/report/{astronaut_id}")
def report(astronaut_id: str):
    return db.get_mission_report(astronaut_id)


# Privacy screen
@app.post("/privacy")
def privacy(data: PrivacyIn):
    db.set_privacy(data.astronaut_id, data.share_mood, data.share_sleep)
    return {"saved": True}


# Contact a doctor button
@app.post("/contact-doctor")
def contact_doctor(data: MessageIn):
    db.add_to_outbox(data.astronaut_id, data.message, urgency="contact")
    return {"queued": True, "note": "Will reach Earth after the delay"}


# Inbox: doctor replies that have arrived
@app.get("/inbox/{astronaut_id}")
def inbox(astronaut_id: str):
    return db.get_inbox(astronaut_id)


# Earth link: send every message whose delay is over
# (the React app can call this every few seconds)
@app.post("/send-to-earth")
def send_to_earth():
    return db.send_ready_messages()


# Demo only: pretend to be a doctor on Earth replying
@app.post("/demo/doctor-reply")
def demo_doctor_reply(data: MessageIn):
    db.doctor_reply(data.astronaut_id, data.message)
    return {"reply_on_the_way": True}
