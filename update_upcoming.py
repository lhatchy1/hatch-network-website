#!/usr/bin/env python3
"""
Upcoming Seasons Updater for Firebase

Two feeds, written to the Firebase Realtime Database so the website can render
them without needing an API key of its own:

  upcoming        - TV shows already in the Plex library that have a new season
                    on the way (TVmaze, no key needed)
  upcomingMovies  - upcoming cinema and digital film releases in your region,
                    by popularity (TMDB, free API key needed)

The film feed is skipped, with a note, until TMDB_API_KEY is set.

Designed to run alongside update_plex_stats.py on the Plex server, but on a
daily schedule rather than every 30 minutes (air dates rarely change hourly,
and TVmaze is a free service worth being gentle with).
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

import requests
from plexapi.server import PlexServer
import firebase_admin
from firebase_admin import credentials, db

# ========================================
# CONFIGURATION - UPDATE THESE VALUES
# ========================================

# Plex Server Configuration
PLEX_URL = os.environ.get('PLEX_URL', 'http://localhost:32400')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN', 'YOUR_PLEX_TOKEN_HERE')

# Firebase Configuration
FIREBASE_DATABASE_URL = 'https://hatch-network-website-default-rtdb.europe-west1.firebasedatabase.app'
FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get(
    'FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-service-account.json')

# TV library names to scan (must match your Plex library names)
TV_LIBRARY_NAMES = ['TV Shows']

# Only report seasons airing within this many days
MAX_DAYS_AHEAD = 365

# Where to remember Plex show -> TVmaze show ID lookups between runs
CACHE_PATH = os.environ.get('UPCOMING_CACHE_PATH', 'tvmaze_cache.json')

# TMDB (films) - free key from https://www.themoviedb.org/settings/api
# Either the v3 "API Key" or the v4 "Read Access Token" works here.
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'YOUR_TMDB_API_KEY_HERE')

# Region whose release dates to use (ISO 3166-1), and language for titles
MOVIE_REGION = 'CH'
MOVIE_LANGUAGE = 'en-GB'

# Only report films releasing within this many days, and at most this many
MAX_MOVIE_DAYS_AHEAD = 120
MAX_MOVIES = 30

# ========================================
# TVMAZE HELPERS
# ========================================

TVMAZE_BASE = 'https://api.tvmaze.com'

# TVmaze allows roughly 20 calls per 10 seconds; stay comfortably inside that
TVMAZE_DELAY_SECONDS = 0.5

_session = requests.Session()
_session.headers.update({'User-Agent': 'HatchNetwork-UpcomingSeasons/1.0'})


def tvmaze_get(path, params=None):
    """GET a TVmaze endpoint, returning None on 404 and retrying on rate limits."""
    url = f'{TVMAZE_BASE}{path}'

    for attempt in range(3):
        time.sleep(TVMAZE_DELAY_SECONDS)
        try:
            response = _session.get(url, params=params, timeout=20)
        except requests.RequestException as e:
            print(f'[TVmaze] Request failed ({e}); retrying...')
            time.sleep(2 ** attempt)
            continue

        if response.status_code == 404:
            return None
        if response.status_code == 429:
            print('[TVmaze] Rate limited; backing off...')
            time.sleep(5 * (attempt + 1))
            continue
        if response.ok:
            return response.json()

        print(f'[TVmaze] Unexpected status {response.status_code} for {url}')
        time.sleep(2 ** attempt)

    return None


def load_cache():
    """Load the Plex-to-TVmaze ID cache, tolerating a missing or corrupt file."""
    try:
        with open(CACHE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        print(f'[Cache] Could not write {CACHE_PATH}: {e}')


def extract_external_ids(show):
    """Pull TheTVDB and IMDb IDs out of a Plex show's GUIDs, if present."""
    ids = {}

    guids = []
    try:
        guids = [g.id for g in (show.guids or [])]
    except (AttributeError, TypeError):
        pass

    # Older Plex agents only expose a single legacy guid string
    legacy = getattr(show, 'guid', None)
    if legacy:
        guids.append(legacy)

    for guid in guids:
        tvdb = re.search(r'(?:thetvdb|tvdb)://(\d+)', guid)
        if tvdb:
            ids['thetvdb'] = tvdb.group(1)
        imdb = re.search(r'imdb://(tt\d+)', guid)
        if imdb:
            ids['imdb'] = imdb.group(1)

    return ids


def resolve_tvmaze_id(show, cache):
    """Find the TVmaze ID for a Plex show, using the cache where possible."""
    cache_key = str(show.ratingKey)
    if cache_key in cache:
        return cache[cache_key]

    tvmaze_id = None
    ids = extract_external_ids(show)

    if 'thetvdb' in ids:
        match = tvmaze_get('/lookup/shows', {'thetvdb': ids['thetvdb']})
        tvmaze_id = match.get('id') if match else None

    if tvmaze_id is None and 'imdb' in ids:
        match = tvmaze_get('/lookup/shows', {'imdb': ids['imdb']})
        tvmaze_id = match.get('id') if match else None

    if tvmaze_id is None:
        match = tvmaze_get('/singlesearch/shows', {'q': show.title})
        tvmaze_id = match.get('id') if match else None

    cache[cache_key] = tvmaze_id
    if tvmaze_id is None:
        print(f'[TVmaze] No match for "{show.title}"')

    return tvmaze_id


# ========================================
# TMDB HELPERS (films)
# ========================================

TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_DELAY_SECONDS = 0.1

# TMDB release types: 2 = theatrical (limited), 3 = theatrical, 4 = digital
CINEMA_RELEASE_TYPES = {2, 3}
DIGITAL_RELEASE_TYPES = {4}


def tmdb_configured():
    return bool(TMDB_API_KEY) and TMDB_API_KEY != 'YOUR_TMDB_API_KEY_HERE'


def tmdb_get(path, params=None):
    """GET a TMDB endpoint, returning None on 404 and retrying on rate limits."""
    params = dict(params or {})
    headers = {}
    # v4 read access tokens are JWTs and go in a header; v3 keys go in the query
    if TMDB_API_KEY.startswith('eyJ'):
        headers['Authorization'] = f'Bearer {TMDB_API_KEY}'
    else:
        params['api_key'] = TMDB_API_KEY

    url = f'{TMDB_BASE}{path}'

    for attempt in range(3):
        time.sleep(TMDB_DELAY_SECONDS)
        try:
            response = _session.get(url, params=params, headers=headers, timeout=20)
        except requests.RequestException as e:
            print(f'[TMDB] Request failed ({e}); retrying...')
            time.sleep(2 ** attempt)
            continue

        if response.status_code == 404:
            return None
        if response.status_code == 401:
            print('[TMDB] Unauthorised - check TMDB_API_KEY')
            return None
        if response.status_code == 429:
            print('[TMDB] Rate limited; backing off...')
            time.sleep(5 * (attempt + 1))
            continue
        if response.ok:
            return response.json()

        print(f'[TMDB] Unexpected status {response.status_code} for {url}')
        time.sleep(2 ** attempt)

    return None


def parse_iso_date(raw):
    try:
        return datetime.strptime((raw or '')[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def regional_release_dates(movie_id, today, horizon):
    """Earliest upcoming cinema and digital dates for MOVIE_REGION, or None."""
    data = tmdb_get(f'/movie/{movie_id}/release_dates')
    cinema = digital = None

    for country in (data or {}).get('results', []):
        if country.get('iso_3166_1') != MOVIE_REGION:
            continue
        for release in country.get('release_dates', []):
            when = parse_iso_date(release.get('release_date'))
            if when is None or not (today <= when <= horizon):
                continue
            kind = release.get('type')
            if kind in CINEMA_RELEASE_TYPES and (cinema is None or when < cinema):
                cinema = when
            elif kind in DIGITAL_RELEASE_TYPES and (digital is None or when < digital):
                digital = when

    return cinema, digital


def scan_upcoming_movies():
    """Most popular films releasing in the region soon, or None if TMDB isn't set up."""
    if not tmdb_configured():
        print('[TMDB] No API key set - skipping films (set TMDB_API_KEY to enable)')
        return None

    today = date.today()
    horizon = today + timedelta(days=MAX_MOVIE_DAYS_AHEAD)

    genre_list = tmdb_get('/genre/movie/list', {'language': MOVIE_LANGUAGE}) or {}
    genres = {g['id']: g['name'] for g in genre_list.get('genres', []) if 'id' in g and 'name' in g}

    candidates = []
    for page in (1, 2, 3):
        data = tmdb_get('/discover/movie', {
            'region': MOVIE_REGION,
            'language': MOVIE_LANGUAGE,
            'with_release_type': '2|3|4',
            'release_date.gte': today.isoformat(),
            'release_date.lte': horizon.isoformat(),
            'sort_by': 'popularity.desc',
            'page': page,
        })
        if not data:
            break
        candidates.extend(data.get('results', []))
        if page >= (data.get('total_pages') or 1):
            break

    print(f'[TMDB] {len(candidates)} candidate film(s) in the next {MAX_MOVIE_DAYS_AHEAD} days')

    movies = []
    for candidate in candidates:
        if len(movies) >= MAX_MOVIES:
            break

        title = candidate.get('title')
        movie_id = candidate.get('id')
        if not title or not movie_id:
            continue

        cinema, digital = regional_release_dates(movie_id, today, horizon)

        if cinema is None and digital is None:
            # Regional detail is thin for this one - trust the date discover gave us
            cinema = parse_iso_date(candidate.get('release_date'))
            if cinema is None or not (today <= cinema <= horizon):
                continue

        primary = min(d for d in (cinema, digital) if d is not None)

        entry = {
            'title': title,
            'tmdbId': movie_id,
            'releaseDate': primary.isoformat(),
            'releaseType': 'cinema' if primary == cinema else 'digital',
            'popularity': round(candidate.get('popularity') or 0, 1),
        }
        if cinema:
            entry['cinemaDate'] = cinema.isoformat()
        if digital:
            entry['digitalDate'] = digital.isoformat()

        names = [genres[g] for g in candidate.get('genre_ids', []) if g in genres][:3]
        if names:
            entry['genres'] = names

        print(f'[Found] {title} - {entry["releaseType"]} {entry["releaseDate"]}')
        movies.append(entry)

    movies.sort(key=lambda entry: (entry['releaseDate'], entry['title']))
    return movies


def comparable_movies(movies):
    return [(m.get('title'), m.get('releaseType'), m.get('releaseDate')) for m in movies]


# ========================================
# PLEX HELPERS
# ========================================

def highest_season_on_server(show):
    """Highest real season number in the library (specials are season 0)."""
    try:
        numbers = [s.seasonNumber for s in show.seasons()
                   if s.seasonNumber is not None and s.seasonNumber > 0]
        return max(numbers) if numbers else 0
    except Exception as e:
        print(f'[Plex] Could not read seasons for "{show.title}": {e}')
        return 0


def get_tv_shows(plex):
    """Collect every show across the configured TV libraries."""
    shows = []

    for section in plex.library.sections():
        if section.type == 'show' and section.title in TV_LIBRARY_NAMES:
            print(f'[Plex] Scanning library "{section.title}"...')
            shows.extend(section.all())

    if not shows:
        print(f'[Plex] No shows found in libraries {TV_LIBRARY_NAMES}')

    return shows


# ========================================
# CORE LOGIC
# ========================================

def find_next_season(show, tvmaze_id, owned_season):
    """Return the next announced season premiere beyond what's on the server."""
    details = tvmaze_get(f'/shows/{tvmaze_id}', {'embed': 'episodes'})
    if not details:
        return None

    episodes = (details.get('_embedded') or {}).get('episodes') or []
    today = date.today()
    horizon = today + timedelta(days=MAX_DAYS_AHEAD)

    candidates = []
    for episode in episodes:
        # Season premieres only - this view is about new seasons, not weekly episodes
        if episode.get('number') != 1:
            continue

        season = episode.get('season')
        airdate = episode.get('airdate')
        if not season or not airdate:
            continue

        # Only seasons the server doesn't already have
        if season <= owned_season:
            continue

        try:
            air = datetime.strptime(airdate, '%Y-%m-%d').date()
        except ValueError:
            continue

        if today <= air <= horizon:
            candidates.append((air, season, episode))

    if not candidates:
        return None

    air, season, episode = min(candidates, key=lambda c: c[0])
    network = (details.get('network') or details.get('webChannel') or {}).get('name')

    entry = {
        'title': show.title,
        'season': season,
        'airDate': air.isoformat(),
        'seasonsOnServer': owned_season,
    }
    if network:
        entry['network'] = network
    if episode.get('name'):
        entry['episodeTitle'] = episode['name']

    return entry


def scan_upcoming(plex, cache):
    """Build the list of returning seasons for shows already in the library."""
    shows = get_tv_shows(plex)
    print(f'[Plex] Checking {len(shows)} show(s) against TVmaze...')

    upcoming = []
    for index, show in enumerate(shows, start=1):
        if index % 25 == 0:
            print(f'[Scan] {index}/{len(shows)} checked, {len(upcoming)} found so far')

        tvmaze_id = resolve_tvmaze_id(show, cache)
        if not tvmaze_id:
            continue

        owned_season = highest_season_on_server(show)

        try:
            entry = find_next_season(show, tvmaze_id, owned_season)
        except Exception as e:
            print(f'[Scan] Error checking "{show.title}": {e}')
            continue

        if entry:
            print(f'[Found] {entry["title"]} - season {entry["season"]} on {entry["airDate"]}')
            upcoming.append(entry)

    upcoming.sort(key=lambda entry: (entry['airDate'], entry['title']))
    return upcoming


def comparable(shows):
    """Normalise the list so unchanged scans don't look like changes."""
    return [(s['title'], s['season'], s['airDate']) for s in shows]


# ========================================
# FIREBASE
# ========================================

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DATABASE_URL
        })


def write_feed(node, list_key, items, fingerprint):
    """Write a feed, only bumping changedAt when its contents actually changed."""
    ref = db.reference(node)
    existing = ref.get() or {}
    existing_items = existing.get(list_key) or []
    if isinstance(existing_items, dict):
        existing_items = list(existing_items.values())

    now_ms = int(time.time() * 1000)
    changed = fingerprint(existing_items) != fingerprint(items)

    ref.set({
        'updatedAt': now_ms,
        'changedAt': now_ms if changed else existing.get('changedAt', now_ms),
        list_key: items,
    })

    state = 'list changed' if changed else 'no change'
    print(f'[Firebase] {node}: {len(items)} item(s) - {state}')


# ========================================
# MAIN SCRIPT
# ========================================

def main():
    print('=' * 50)
    print('Upcoming Seasons Updater')
    print('=' * 50)

    try:
        print('[Plex] Connecting to Plex server...')
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    except Exception as e:
        print(f'[Plex] Error connecting to Plex: {e}')
        sys.exit(1)

    cache = load_cache()

    try:
        upcoming = scan_upcoming(plex, cache)
    finally:
        # Keep whatever lookups we managed, even if the scan died part-way
        save_cache(cache)

    try:
        print('[Firebase] Initializing Firebase...')
        init_firebase()
        write_feed('upcoming', 'shows', upcoming, comparable)
    except Exception as e:
        print(f'[Firebase] Error updating Firebase: {e}')
        sys.exit(1)

    # Films are independent of the TV scan - a TMDB problem must not undo the above
    try:
        movies = scan_upcoming_movies()
    except Exception as e:
        print(f'[TMDB] Film scan failed: {e}')
        movies = None

    if movies is not None:
        try:
            write_feed('upcomingMovies', 'movies', movies, comparable_movies)
        except Exception as e:
            print(f'[Firebase] Error writing films: {e}')
            sys.exit(1)

    print('[Success] Upcoming feeds updated!')
    print('=' * 50)


if __name__ == '__main__':
    main()
