"""
database.py  -  the DATABASE part of the astronaut health app.

What this file does (in simple words):
  1. Creates one database file called  astro.db  (like one Excel file).
  2. Puts 5 tables inside it (like 5 sheets).
  3. Fills them with FAKE mission data so the app has something to show.
  4. Gives the other team members simple FUNCTIONS (buttons) to save and read data,
     so they never have to write database code themselves.

How to run it:   python database.py
Works offline. Needs nothing to install (sqlite3 comes with Python).
"""

import random
import sqlite3
import time

DB_FILE = "astro.db"


# ---------------------------------------------------------------------------
# 0. Open the database file (creates it if it does not exist yet)
# ---------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us read columns by name, e.g. row["mood"]
    return conn


# ---------------------------------------------------------------------------
# 1. Create the 5 tables (the 5 "sheets")
# ---------------------------------------------------------------------------
def create_tables():
    conn = connect()
    conn.executescript("""
    -- Sheet 1: who is on the crew + their privacy switches (1 = share, 0 = keep private)
    CREATE TABLE IF NOT EXISTS astronauts (
        id          TEXT PRIMARY KEY,
        name        TEXT,
        role        TEXT,
        username    TEXT,              -- for login
        pin         TEXT,              -- 4-digit login code (demo only)
        share_mood  INTEGER DEFAULT 1,
        share_sleep INTEGER DEFAULT 1
    );

    -- Sheet 2: what was measured each day (one row per astronaut per day)
    CREATE TABLE IF NOT EXISTS daily_readings (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        astronaut_id  TEXT,
        day           INTEGER,
        sleep_hours   REAL,
        heart_rate    INTEGER,
        mood          INTEGER,     -- 1 (very bad) to 5 (very good)
        stress        INTEGER,     -- 1 (calm) to 5 (very stressed)
        miss_family   INTEGER,     -- 1 (fine) to 5 (miss them a lot)
        feeling       TEXT,        -- one word from the check-in game, e.g. "tired"
        reaction_ms   INTEGER,     -- tap-game speed, lower = faster
        radiation_msv REAL,        -- radiation dose that day
        exercise_min  INTEGER,
        co2_ppm       INTEGER,     -- cabin carbon dioxide
        FOREIGN KEY (astronaut_id) REFERENCES astronauts(id)
    );

    -- Sheet 3: the 5 RIDGE dial scores for each day (0 = safe, 100 = danger)
    CREATE TABLE IF NOT EXISTS dial_scores (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        astronaut_id TEXT,
        day          INTEGER,
        radiation    INTEGER,
        isolation    INTEGER,
        distance     INTEGER,
        gravity      INTEGER,
        environment  INTEGER,
        FOREIGN KEY (astronaut_id) REFERENCES astronauts(id)
    );

    -- Sheet 4: action cards
    CREATE TABLE IF NOT EXISTS alerts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        astronaut_id TEXT,
        day          INTEGER,
        kind         TEXT DEFAULT 'guidance',  -- guidance / reminder
        hazard       TEXT,     -- radiation / isolation / distance / gravity / environment
        level        TEXT,     -- watch / act_now
        action       TEXT,     -- what the astronaut should do
        done         INTEGER DEFAULT 0,
        FOREIGN KEY (astronaut_id) REFERENCES astronauts(id)
    );

    -- Sheet 5: messages waiting to go to Earth
    CREATE TABLE IF NOT EXISTS outbox (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        astronaut_id TEXT,
        message      TEXT,
        urgency      TEXT DEFAULT 'daily',  -- daily / watch / urgent / contact
        send_after   INTEGER,  -- time (in seconds) when it is allowed to be sent
        sent         INTEGER DEFAULT 0,
        FOREIGN KEY (astronaut_id) REFERENCES astronauts(id)
    );

    -- Sheet 6: replies from doctors on Earth (arrive after the delay)
    CREATE TABLE IF NOT EXISTS inbox (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        astronaut_id TEXT,
        message      TEXT,
        arrive_after INTEGER,  -- time (in seconds) when the astronaut can see it
        read         INTEGER DEFAULT 0,
        FOREIGN KEY (astronaut_id) REFERENCES astronauts(id)
    );
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 2. Fill the database with a FAKE 180-day mission
# ---------------------------------------------------------------------------
def add_fake_mission(days=180):
    conn = connect()
    # Start clean so running the file twice does not double the data
    for table in ["inbox", "outbox", "alerts", "dial_scores", "daily_readings", "astronauts"]:
        conn.execute(f"DELETE FROM {table}")

    crew = [
        ("A1", "Sara", "Crew medical officer", "sara", "1111"),
        ("A2", "Omar", "Commander", "omar", "2222"),
    ]
    conn.executemany(
        "INSERT INTO astronauts (id, name, role, username, pin) VALUES (?, ?, ?, ?, ?)", crew
    )

    random.seed(7)  # same fake data every time, so the demo is repeatable
    for astronaut_id, *_ in crew:
        for day in range(1, days + 1):
            # Days 1-14 = "pre-flight": this is where the app learns each person's normal.
            mid_mission_dip = 1.0 if 60 <= day <= 100 else 0.0  # a tough period mid-mission
            solar_storm = day in (75, 140)                       # two radiation spikes

            sleep = round(random.gauss(7.0 - 1.3 * mid_mission_dip, 0.4), 1)
            mood = max(1, min(5, round(random.gauss(4 - 1.5 * mid_mission_dip, 0.5))))
            reaction = int(random.gauss(280 + 50 * mid_mission_dip, 15))
            heart = int(random.gauss(64 + 5 * mid_mission_dip, 3))
            radiation = round(random.gauss(0.5, 0.05) * (8 if solar_storm else 1), 2)
            exercise = int(random.gauss(120 - 40 * mid_mission_dip, 10))
            co2 = int(random.gauss(2500, 200) + (1500 if day in (30, 31) else 0))
            stress = max(1, min(5, round(random.gauss(2 + 1.5 * mid_mission_dip, 0.6))))
            miss_family = max(1, min(5, round(random.gauss(2 + day / 90 + mid_mission_dip, 0.6))))
            if mid_mission_dip:
                feeling = random.choice(["tired", "lonely", "stressed", "okay"])
            else:
                feeling = random.choice(["happy", "calm", "okay", "focused"])

            conn.execute(
                """INSERT INTO daily_readings
                   (astronaut_id, day, sleep_hours, heart_rate, mood, stress, miss_family,
                    feeling, reaction_ms, radiation_msv, exercise_min, co2_ppm)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (astronaut_id, day, sleep, heart, mood, stress, miss_family, feeling,
                 reaction, radiation, exercise, co2),
            )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 3. FUNCTIONS FOR THE TEAM  (the "buttons" other members call)
#    Member B (brain) and Member C (screens) only use these. No SQL needed.
# ---------------------------------------------------------------------------

# ----- astronauts -----
def get_astronauts():
    """List of everyone on the crew."""
    conn = connect()
    rows = conn.execute("SELECT * FROM astronauts").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def login(username, pin):
    """Login screen: returns the astronaut if username + pin are right, else None."""
    conn = connect()
    row = conn.execute(
        "SELECT id, name, role FROM astronauts WHERE username = ? AND pin = ?",
        (username, pin),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_privacy(astronaut_id, share_mood, share_sleep):
    """Privacy screen: 1 = send to Earth, 0 = keep private."""
    conn = connect()
    conn.execute(
        "UPDATE astronauts SET share_mood = ?, share_sleep = ? WHERE id = ?",
        (share_mood, share_sleep, astronaut_id),
    )
    conn.commit()
    conn.close()


# ----- daily readings -----
def save_reading(astronaut_id, day, sleep_hours, heart_rate, mood, stress, miss_family,
                 feeling, reaction_ms, radiation_msv, exercise_min, co2_ppm):
    """Check-in game: save one new day."""
    conn = connect()
    conn.execute(
        """INSERT INTO daily_readings
           (astronaut_id, day, sleep_hours, heart_rate, mood, stress, miss_family,
            feeling, reaction_ms, radiation_msv, exercise_min, co2_ppm)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (astronaut_id, day, sleep_hours, heart_rate, mood, stress, miss_family,
         feeling, reaction_ms, radiation_msv, exercise_min, co2_ppm),
    )
    conn.commit()
    conn.close()


def get_readings(astronaut_id, from_day=1, to_day=10_000):
    """Brain + History screen: get the readings between two days."""
    conn = connect()
    rows = conn.execute(
        """SELECT * FROM daily_readings
           WHERE astronaut_id = ? AND day BETWEEN ? AND ?
           ORDER BY day""",
        (astronaut_id, from_day, to_day),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ----- dial scores -----
def save_dial_scores(astronaut_id, day, radiation, isolation, distance, gravity, environment):
    """Brain: save the 5 dial numbers for one day."""
    conn = connect()
    conn.execute(
        """INSERT INTO dial_scores
           (astronaut_id, day, radiation, isolation, distance, gravity, environment)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (astronaut_id, day, radiation, isolation, distance, gravity, environment),
    )
    conn.commit()
    conn.close()


def get_dial_scores(astronaut_id, day):
    """Dashboard: get the 5 dial numbers for one day (or None if not calculated yet)."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM dial_scores WHERE astronaut_id = ? AND day = ?",
        (astronaut_id, day),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ----- alerts (action cards) -----
def save_alert(astronaut_id, day, hazard, level, action, kind="guidance"):
    """Brain: create a new action card. kind = "guidance" or "reminder" (exercise/sleep)."""
    conn = connect()
    conn.execute(
        "INSERT INTO alerts (astronaut_id, day, kind, hazard, level, action) VALUES (?, ?, ?, ?, ?, ?)",
        (astronaut_id, day, kind, hazard, level, action),
    )
    conn.commit()
    conn.close()


def get_open_alerts(astronaut_id):
    """Dashboard: action cards the astronaut has not ticked off yet."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE astronaut_id = ? AND done = 0 ORDER BY day DESC",
        (astronaut_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alert_done(alert_id):
    """Dashboard: astronaut ticks a card as done."""
    conn = connect()
    conn.execute("UPDATE alerts SET done = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


# ----- mission health report -----
def get_mission_report(astronaut_id):
    """Mission report screen: simple averages over the whole mission."""
    conn = connect()
    row = conn.execute(
        """SELECT COUNT(*)                     AS days,
                  ROUND(AVG(sleep_hours), 1)   AS avg_sleep,
                  ROUND(AVG(mood), 1)          AS avg_mood,
                  ROUND(AVG(stress), 1)        AS avg_stress,
                  ROUND(AVG(exercise_min))     AS avg_exercise,
                  ROUND(SUM(radiation_msv), 1) AS total_radiation
           FROM daily_readings WHERE astronaut_id = ?""",
        (astronaut_id,),
    ).fetchone()
    conn.close()
    return dict(row)


# ----- outbox (messages to Earth) -----
def add_to_outbox(astronaut_id, message, urgency="daily", delay_seconds=20):
    """Earth link: put a message in the outbox. 20 seconds = fake Mars delay for the demo.
    urgency: "daily" (summary), "watch" (getting worse), "urgent" (red dial),
             "contact" (astronaut pressed Contact doctor)."""
    conn = connect()
    conn.execute(
        "INSERT INTO outbox (astronaut_id, message, urgency, send_after) VALUES (?, ?, ?, ?)",
        (astronaut_id, message, urgency, int(time.time()) + delay_seconds),
    )
    conn.commit()
    conn.close()


def send_ready_messages():
    """Earth link: 'send' every message whose delay is over. Returns what was sent."""
    conn = connect()
    now = int(time.time())
    rows = conn.execute(
        "SELECT * FROM outbox WHERE sent = 0 AND send_after <= ?", (now,)
    ).fetchall()
    conn.execute("UPDATE outbox SET sent = 1 WHERE sent = 0 AND send_after <= ?", (now,))
    conn.commit()
    conn.close()
    return [dict(r) for r in rows]


# ----- inbox (replies from doctors on Earth) -----
def doctor_reply(astronaut_id, message, delay_seconds=20):
    """Earth doctor side (for the demo): send a reply that arrives after the delay."""
    conn = connect()
    conn.execute(
        "INSERT INTO inbox (astronaut_id, message, arrive_after) VALUES (?, ?, ?)",
        (astronaut_id, message, int(time.time()) + delay_seconds),
    )
    conn.commit()
    conn.close()


def get_inbox(astronaut_id):
    """Astronaut app: doctor replies that have arrived (delay is over)."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM inbox WHERE astronaut_id = ? AND arrive_after <= ? ORDER BY id DESC",
        (astronaut_id, int(time.time())),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Run this file directly to build the database and check it works
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    create_tables()
    add_fake_mission(days=180)

    print("Database created:", DB_FILE)
    print("Crew:", [a["name"] for a in get_astronauts()])
    day42 = get_readings("A1", 42, 42)[0]
    print("Sara, day 42:", {k: day42[k] for k in ("sleep_hours", "mood", "stress", "miss_family", "feeling")})
    print("Readings stored for Sara:", len(get_readings("A1")), "days")
    print("Login test:", login("sara", "1111"))
    print("Mission report:", get_mission_report("A1"))
