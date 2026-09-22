# Upcoming Seasons Setup Guide

This guide covers the **UPCOMING** tab on the website, which shows new seasons
on the way for TV shows that are *already in the Plex library*.

## Overview

1. `update_upcoming.py` runs on the Plex server (same box as `update_plex_stats.py`)
2. It walks the TV libraries and asks [TVmaze](https://www.tvmaze.com/api) whether
   each show has a season premiere announced beyond what the server already has
3. Results are written to the `upcoming` node in Firebase
4. The website reads that node and renders the UPCOMING tab
5. Windows Task Scheduler runs the script **once a day**

Because the lookup happens server-side, no API key ever reaches the public site,
and the list only ever contains shows you actually own.

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

Add the `upcoming` node to your Firebase Realtime Database rules (the full rule
set lives in [FIREBASE_RULES.json](FIREBASE_RULES.json)):

```json
"upcoming": {
  ".read": true,
  ".write": false
}
```

Public read, service-account-only write &mdash; exactly like `plexStats`.

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

Two constants have no environment variable and must be edited in the file if the
defaults don't suit:

- `TV_LIBRARY_NAMES` &mdash; must match your Plex TV library names exactly
- `MAX_DAYS_AHEAD` &mdash; how far ahead to look (default 365 days)

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
[Firebase] Updated with 7 season(s) - list changed
[Success] Upcoming seasons updated!
==================================================
```

The first run is the slow one &mdash; every show needs a TVmaze search. Show IDs
are then cached in `tvmaze_cache.json`, so later runs are considerably quicker.

Check the UPCOMING tab on the website; the results should appear immediately.

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

The script writes a single `upcoming` node:

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

- `updatedAt` is bumped on **every** run, and drives the "Last scanned" line
- `changedAt` is bumped **only** when the list of (title, season, air date)
  actually differs. That is what drives the green notification pip on the tab,
  so a daily scan that finds nothing new doesn't nag anyone

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

## Troubleshooting

### "No match for ..." in the output

TVmaze couldn't identify that show. Usually harmless (documentaries and
obscure imports are the common culprits). To force a re-match after fixing the
show's metadata in Plex, delete `tvmaze_cache.json` and run again.

### The tab says "NO UPCOMING SEASONS FOUND"

The `upcoming` node doesn't exist yet &mdash; run the script manually once.

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
