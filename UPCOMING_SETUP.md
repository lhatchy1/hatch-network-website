# Upcoming Seasons Setup Guide

This guide covers the **UPCOMING** tab on the website. It has two sub-tabs:

- **TV SHOWS** &mdash; new seasons on the way for shows *already in the Plex library*
- **MOVIES** &mdash; upcoming cinema and digital film releases in your region, by popularity

## Overview

1. `update_upcoming.py` runs on the Plex server (same box as `update_plex_stats.py`)
2. For TV, it walks the libraries and asks [TVmaze](https://www.tvmaze.com/api) whether
   each show has a season premiere announced beyond what the server already has
3. For films, it asks [TMDB](https://www.themoviedb.org/) for the most popular releases
   in the next few months and looks up each one's cinema and digital dates for your region
4. Results are written to the `upcoming` and `upcomingMovies` nodes in Firebase
5. The website reads those nodes and renders the two sub-tabs
6. Windows Task Scheduler runs the script **once a day**

Because the lookups happen server-side, no API key ever reaches the public site.
The TV list only ever contains shows you actually own.

### Why once a day, not every 30 minutes

TVmaze is free and has no API key, but it does rate limit (roughly 20 calls per
10 seconds). A full scan makes one or two calls per show. Air dates change on the
scale of weeks, so a daily scan is plenty and keeps us a good neighbour. The
script already sleeps between calls and backs off on HTTP 429.

## Prerequisites

You should have already completed [PLEX_STATS_SETUP.md](PLEX_STATS_SETUP.md).
This script reuses the same Python install, the same
`firebase-service-account.json`, and the same working directory.

## Step 1: Install Dependencies

`requests` comes in with `plexapi`, so if the stats script works you already
have everything:

```powershell
pip install plexapi firebase-admin requests
```

## Step 2: Update Firebase Rules

Add the `upcoming` and `upcomingMovies` nodes to your Firebase Realtime Database
rules (the full rule set lives in [FIREBASE_RULES.json](FIREBASE_RULES.json)):

```json
"upcoming": {
  ".read": true,
  ".write": false
},
"upcomingMovies": {
  ".read": true,
  ".write": false
}
```

Public read, service-account-only write &mdash; exactly like `plexStats`.

## Step 2b: Get a TMDB API Key (for films)

TVmaze needs no key, but TMDB does. It's free and takes a couple of minutes:

1. Create an account at [themoviedb.org](https://www.themoviedb.org/signup)
2. Go to **Settings &rarr; API** ([direct link](https://www.themoviedb.org/settings/api))
3. Request a key &mdash; choose **Developer**, fill in the short form (personal use is fine)
4. Copy either the **API Key** (v3) or the **API Read Access Token** (v4). The script
   accepts both.

Without a key the script still runs and updates TV; it just prints
`[TMDB] No API key set - skipping films` and leaves the MOVIES tab on its
"scan may not have run yet" message.

## Step 3: Configure the Script

Copy `update_upcoming.py` to the same folder as `update_plex_stats.py`
(for example `C:\PlexStats`), then either edit the constants at the top of the
file or set the environment variables:

| Setting | Environment variable | Default |
|---|---|---|
| Plex server URL | `PLEX_URL` | `http://localhost:32400` |
| Plex token | `PLEX_TOKEN` | `YOUR_PLEX_TOKEN_HERE` |
| Service account path | `FIREBASE_SERVICE_ACCOUNT_PATH` | `firebase-service-account.json` |
| Lookup cache path | `UPCOMING_CACHE_PATH` | `tvmaze_cache.json` |
| TMDB API key | `TMDB_API_KEY` | `YOUR_TMDB_API_KEY_HERE` |

These constants have no environment variable and must be edited in the file if
the defaults don't suit:

- `TV_LIBRARY_NAMES` &mdash; must match your Plex TV library names exactly
- `MAX_DAYS_AHEAD` &mdash; how far ahead to look for TV seasons (default 365 days)
- `MOVIE_REGION` &mdash; ISO country code whose release dates to use (default `CH`)
- `MOVIE_LANGUAGE` &mdash; language for film titles (default `en-GB`)
- `MAX_MOVIE_DAYS_AHEAD` &mdash; how far ahead to look for films (default 120 days)
- `MAX_MOVIES` &mdash; how many films to list (default 30)

## Step 4: Test It

```powershell
cd C:\PlexStats
python update_upcoming.py
```

Expected output:

```
==================================================
Upcoming Seasons Updater
==================================================
[Plex] Connecting to Plex server...
[Plex] Scanning library "TV Shows"...
[Plex] Checking 182 show(s) against TVmaze...
[Found] Severance - season 3 on 2026-10-14
[Scan] 25/182 checked, 1 found so far
...
[Firebase] Initializing Firebase...
[Firebase] upcoming: 7 item(s) - list changed
[TMDB] 58 candidate film(s) in the next 120 days
[Found] Dune: Part Three - cinema 2026-12-18
...
[Firebase] upcomingMovies: 30 item(s) - list changed
[Success] Upcoming feeds updated!
==================================================
```

The first run is the slow one &mdash; every show needs a TVmaze search. Show IDs
are then cached in `tvmaze_cache.json`, so later runs are considerably quicker.

Check the UPCOMING tab on the website; both sub-tabs should populate immediately.

## Step 5: Schedule It Daily

Follow the same steps as Step 7 of [PLEX_STATS_SETUP.md](PLEX_STATS_SETUP.md),
with these differences:

- **Name**: `Upcoming Seasons Updater`
- **Trigger**: Daily, recur every 1 day, at around `04:00`. Do **not** tick
  "Repeat task every..."
- **Add arguments**: `update_upcoming.py`

Or via PowerShell as Administrator:

```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Python311\python.exe' `
    -Argument 'update_upcoming.py' `
    -WorkingDirectory 'C:\PlexStats'

$trigger = New-ScheduledTaskTrigger -Daily -At 4am

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" `
    -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName "Upcoming Seasons Updater" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Updates upcoming TV seasons in Firebase once a day"
```

## Data Shape

The script writes two nodes. `upcoming` holds TV:

```json
{
  "updatedAt": 1758499200000,
  "changedAt": 1758326400000,
  "shows": [
    {
      "title": "Severance",
      "season": 3,
      "airDate": "2026-10-14",
      "seasonsOnServer": 2,
      "network": "Apple TV+",
      "episodeTitle": "Cold Harbor"
    }
  ]
}
```

`upcomingMovies` holds films:

```json
{
  "updatedAt": 1758499200000,
  "changedAt": 1758326400000,
  "movies": [
    {
      "title": "Dune: Part Three",
      "tmdbId": 1085868,
      "releaseDate": "2026-12-18",
      "releaseType": "cinema",
      "cinemaDate": "2026-12-18",
      "digitalDate": "2027-02-10",
      "genres": ["Science Fiction", "Adventure"],
      "popularity": 412.7
    }
  ]
}
```

- `releaseDate` / `releaseType` are whichever of cinema or digital comes first;
  the other date, if known, rides along so the site can mention it
- `updatedAt` is bumped on **every** run, and drives the "Last scanned" line
- `changedAt` is bumped **only** when the list actually differs (title, season
  and air date for TV; title, type and date for films). That is what drives the
  green notification pips, so a daily scan that finds nothing new doesn't nag
  anyone. Each sub-tab has its own pip, and the UPCOMING tab's pip rolls them up

## How Shows Are Matched

For each Plex show, in order:

1. TheTVDB ID from the Plex GUID &rarr; TVmaze `/lookup/shows?thetvdb=`
2. IMDb ID from the Plex GUID &rarr; TVmaze `/lookup/shows?imdb=`
3. Title search &rarr; TVmaze `/singlesearch/shows?q=`

The result (including "no match") is cached against the Plex rating key, so a
show is only ever searched once.

A show is reported when TVmaze lists a **season premiere** (episode 1) with an
air date in the future, for a season number **higher than the highest season on
the server**. Mid-season returns and weekly episodes are deliberately left out
&mdash; this view is about new seasons, not a broadcast schedule.

## How Films Are Chosen

Films aren't tied to the library (an unreleased film can't be on the server), so
the list is **popularity-ranked**: TMDB's most popular films with a cinema or
digital release in `MOVIE_REGION` within `MAX_MOVIE_DAYS_AHEAD`, capped at
`MAX_MOVIES`. Each candidate's region-specific release dates are looked up so the
row can say **CINEMA** or **DIGITAL** and mention the other date when known. If
TMDB has no regional detail for a film, the general release date is used.

## Troubleshooting

### "No match for ..." in the output

TVmaze couldn't identify that show. Usually harmless (documentaries and
obscure imports are the common culprits). To force a re-match after fixing the
show's metadata in Plex, delete `tvmaze_cache.json` and run again.

### The tab says "NO UPCOMING SEASONS FOUND" / "NO UPCOMING FILMS FOUND"

That node doesn't exist yet &mdash; run the script manually once. If only the
films one says this, `TMDB_API_KEY` isn't set.

### `[TMDB] Unauthorised - check TMDB_API_KEY`

The key was copied wrong, or the request hasn't been approved yet. Both the v3
key and the v4 token work; make sure you copied the whole thing.

### The tab says "NO NEW SEASONS ANNOUNCED RIGHT NOW"

The scan ran but found nothing. Perfectly normal in a quiet month.

### Nothing updates on the website

- Confirm the Firebase rules include the `upcoming` node
- Check the scheduled task's Last Run Result in Task Scheduler
- Run the script by hand and read the output

### The scan is very slow

The first run searches TVmaze for every show at roughly two per second. A
200-show library takes a few minutes. Later runs use the cache and are much
faster.
