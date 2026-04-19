<div align="center">

<img src="https://upload.wikimedia.org/wikipedia/commons/0/09/YouTube_full-color_icon_%282017%29.svg" width="80" alt="YT-Safe Logo" style="display:none"/>

```
 __     _________     _____         ______ ______ 
 \ \   / /__   __|   / ____|  /\   |  ____|  ____|
  \ \_/ /   | |_____| (___   /  \  | |__  | |__   
   \   /    | |______\___ \ / /\ \ |  __| |  __|  
    | |     | |      ____) / ____ \| |    | |____ 
          |_|     |_|     |_____/_/    \_\_|    |______|                         
```

### *A safety-first YouTube clone with a smarter, kinder algorithm.*

<br/>

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2026-FF0000?style=for-the-badge&logo=youtube&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2ecc71?style=for-the-badge)

<br/>

[**Quick Start**](#-quick-start) · [**How It Works**](#-how-the-algorithm-works) · [**Safety System**](#%EF%B8%8F-the-safety-system) · [**File Structure**](#-file-structure) · [**Tests**](#-running-tests)

<br/>

---

</div>

<br/>

## What Is YT-Safe?

> YT-Safe is a **fully functional YouTube frontend** built in Python + Flask, powered by `yt-dlp` for video streaming — with one key difference: **it actually cares about you.**

Instead of maximising watch time at all costs, YT-Safe:

- **Learns your taste** using a hybrid Markov Chain + TF-IDF recommendation engine
- **Enforces healthy breaks** based on attention span and time of day
-  **Gives parents real controls** — not just a PIN screen
-  **Actively suppresses** content you've disliked
-  **Decays old history** so your feed stays fresh and relevant
- **Searches in 8 independent topic batches** for genuine feed diversity

<br/>

---

<br/>

## Quick Start

```bash
# 1 · Clone the repo
git clone https://github.com/yourname/yt-safe.git
cd yt-safe

# 2 · Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows → venv\Scripts\activate

# 3 · Install dependencies
pip install -r requirements.txt

# 4 · Launch
python app.py
```

Then open **[http://localhost:5000](http://localhost:5000)** in your browser.

> **No API key required.** Everything goes through `yt-dlp`.

<br/>

---

<br/>

## How the Algorithm Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WATCH EVENT                                  │
│   A: watch_time  B: video_duration  D: title  E: hashtags           │
│   F: liked       G: disliked        H: hour                         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HISTORY WEIGHTING                                 │
│                                                                     │
│   weight = 0.5 ^ (age_days / 3)   ← 3-day half-life decay          │
│          × like_multiplier (1.5 if liked)                           │
│          × completion_ratio (how much was watched)                  │
│                                                                     │
│   Yesterday's video:  weight ≈ 0.79                                 │
│   3 days ago:         weight = 0.50                                 │
│   1 week ago:         weight ≈ 0.22                                 │
│   2 weeks ago:        weight ≈ 0.05  (near-irrelevant)             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
┌──────────────────────┐   ┌──────────────────────────┐
│    MARKOV CHAIN       │   │        TF-IDF             │
│                       │   │                           │
│  Bigram model trained │   │  Finds words that are     │
│  on weighted corpus.  │   │  characteristic of YOUR   │
│  Captures common      │   │  taste vs. the whole      │
│  word sequences in    │   │  corpus. Stopwords        │
│  your history.        │   │  removed automatically.   │
│                       │   │                           │
│  Top 40 transitions   │   │  Top 40 scored terms      │
└──────────┬───────────┘   └────────────┬─────────────┘
           │                            │
           └──────────┬─────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HYBRID MERGE (50/50)                              │
│                                                                     │
│   score(word) = 0.5 × markov_score_norm + 0.5 × tfidf_score_norm   │
│                                                                     │
│   Disliked word penalties applied → suppressed words filtered out   │
│                                                                     │
│   → 8 output keywords                                               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│               8 INDEPENDENT SEARCH BATCHES  ◇                       │
│                                                                     │
│   keyword[0] → search → 8 videos ┐                                  │
│   keyword[1] → search → 8 videos │                                  │
│   keyword[2] → search → 8 videos │  de-duplicate                   │
│   keyword[3] → search → 8 videos ├──────────────→  FEED            │
│   keyword[4] → search → 8 videos │                                  │
│   keyword[5] → search → 8 videos │                                  │
│   keyword[6] → search → 8 videos │                                  │
│   keyword[7] → search → 8 videos ┘                                  │
└─────────────────────────────────────────────────────────────────────┘
```

> **Cold start:** If you have no watch history, the feed falls back to
> a rotating mix of broad trending queries — no embarrassing blank screen.

<br/>

---

<br/>

## The Safety System

```
┌─────────────────────────────────────────────────────────────────────┐
│                       GUARDRAIL ENGINE                               │
└─────────────────────────────────────────────────────────────────────┘

  After every watch event:

  1.  Throw out watches under 5 seconds  →  not meaningful data

  2.  Calculate attention span %
      ┌──────────────────────────────────────────────┐
      │  attention% = watch_time ÷ video_duration    │
      └──────────────────────────────────────────────┘

  3.  Evaluate triggers
      ┌─────────────────────────────────────────────────────────────┐
      │                                                             │
      │  IF  attention% < 25%                                       │
      │  AND low_attention_minutes > 8                              │
      │  → BREAK  (too much mindless scrolling)                     │
      │                                                             │
      │  IF  total_session_minutes > 20                             │
      │  → BREAK  (hard cap, no exceptions)                         │
      │                                                             │
      └─────────────────────────────────────────────────────────────┘

  4.  Break NEVER cuts a video mid-play.
      The flag is set → enforced by player.js when the video ends.

  5.  Break length scales with time of day:
      ┌───────────────────┬───────────────────────────────────────┐
      │  Time of day      │  Break length                         │
      ├───────────────────┼───────────────────────────────────────┤
      │  Before 6 PM      │  3 minutes  (base)                    │
      │  6 PM → 11 PM     │  Linear scale  3 min → 10 min         │
      │  11 PM +          │  10 minutes (max)                      │
      └───────────────────┴───────────────────────────────────────┘

  6.  Parents can override with fixed presets:
      ┌──────────┬──────────┬──────────┐
      │  10 min  │  30 min  │  60 min  │
      └──────────┴──────────┴──────────┘

  7.  Stats reset to zero after every completed break.
```

<br/>

---

<br/>

## File Structure

```
yt-safe/
│
├── app.py                          Main Flask app & all routes
├── config.py                        All tuneable constants (one place)
├── requirements.txt
│
├── algorithm/                       The brain
│   ├── feed.py                      Hybrid recommender → batch search
│   ├── guardrails.py                Break triggers & session tracking
│   ├── history.py                   Decay-weighted watch history
│   ├── markov.py                    Weighted bigram Markov chain
│   ├── tfidf.py                     Weighted TF-IDF (no sklearn needed)
│   └── trending.py                  Cold-start trending fallback
│
├── video/                           yt-dlp integration
│   ├── fetcher.py                   Stream URL + metadata fetcher
│   ├── embedder.py                  Embed config builder
│   └── search.py                    ytsearch (no API key needed)
│
├── database/                        Storage
│   ├── db.py                        SQLAlchemy init
│   └── models.py                    WatchEvent · SessionStats · ParentSettings
│
├── templates/                       Jinja2 HTML
│   ├── base.html
│   ├── index.html                   Home feed
│   ├── watch.html                   Video player
│   ├── break.html                   Mandatory break screen
│   ├── search.html                  Search results
│   ├── parent_dashboard.html        Parental controls
│   └── components/
│       ├── navbar.html
│       ├── video_card.html
│       └── sidebar.html
│
├── static/
│   ├── css/
│   │   ├── main.css                 Global dark-first design system
│   │   ├── feed.css                 Responsive video grid
│   │   ├── player.css               Custom HTML5 player
│   │   └── break.css                Break + parent dashboard
│   └── js/
│       ├── player.js                Watch tracking · break enforcement
│       ├── feed.js                  Infinite scroll
│       ├── break.js                 Countdown · wellness tips
│       └── guardrails.js            Client-side guardrail helpers
│
└── tests/
    ├── test_guardrails.py
    ├── test_feed.py
    ├── test_markov.py
    └── test_tfidf.py
```

<br/>

---

<br/>

## Running Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run a specific module
python -m pytest tests/test_guardrails.py -v
python -m pytest tests/test_feed.py -v
python -m pytest tests/test_markov.py -v
python -m pytest tests/test_tfidf.py -v

# With coverage report
pip install pytest-cov
python -m pytest tests/ --cov=algorithm --cov-report=term-missing
```

<br/>

---

<br/>

## Routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Home feed |
| `GET` | `/watch/<id>` | Video player |
| `GET` | `/search?q=` | Search results |
| `GET` | `/break` | Mandatory break screen |
| `GET` | `/parent` | Parental dashboard |
| `POST` | `/parent/set_break` | Set parent break preset |
| `POST` | `/api/watch_end` | Record watch event (called by JS) |
| `POST` | `/api/break_complete` | Reset stats after break |
| `GET` | `/api/feed` | JSON feed for infinite scroll |

<br/>

---

<br/>

## Configuration

All settings live in `config.py` — nothing is magic-numbered anywhere else.

```python
# Guardrails
min_watch_seconds          = 5      # Shorter = discarded
low_attention_threshold    = 0.25   # < 25% completion = low attention
low_attention_session_mins = 8      # Minutes of low-attention before break
hard_session_limit_minutes = 20     # Hard cap regardless of attention
break_base_seconds         = 180    # 3 min (daytime)
break_max_seconds          = 600    # 10 min (late night)

# Feed / algorithm
watch_half_life_days   = 3.0   # Decay speed for old watches
num_output_words       = 8     # Keywords the hybrid model outputs
num_batches            = 8     # Search batches (one per keyword)
feed_batch_size        = 8     # Results per batch
markov_weight          = 0.5   # Hybrid split
tfidf_weight           = 0.5
```

<br/>

---

<br/>

## Privacy & Safety Notes

- **No account system.** Sessions are anonymous UUIDs stored in a cookie.
- **No data leaves your machine.** All watch history is stored in a local SQLite file.
- **yt-dlp fetches streams directly.** No third-party tracking scripts.
- **Dislikes are taken seriously.** They actively suppress related content across the whole feed.
- **Breaks cannot be skipped.** The button is disabled until the timer finishes.

<br/>

---

<br/>

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | Web framework |
| `flask-sqlalchemy` | ORM |
| `flask-session` | Server-side sessions |
| `yt-dlp` | Video streaming + search |
| `sqlalchemy` | Database layer |
| `numpy` | Numerical support |
| `apscheduler` | Background task scheduling |
| `python-dotenv` | Environment variable loading |

<br/>

---

<br/>

<div align="center">

**Built with Python · Streamed by yt-dlp**

<br/>

*YT-Safe is not affiliated with yt-dlp, YouTube or Google.*
*This is an independent open-source project.*

</div>
