#!/usr/bin/env python3
"""
Plex Library Stats Updater for Firebase
Queries Plex API for library counts and updates Firebase Realtime Database
"""

import os
import sys
from plexapi.server import PlexServer
import firebase_admin
from firebase_admin import credentials, db

# ========================================
# CONFIGURATION - UPDATE THESE VALUES
# ========================================

# Plex Server Configuration
PLEX_URL = 'http://localhost:32400'  # Your Plex server URL (change if needed)
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'  # Replace with your Plex token

# Firebase Configuration
FIREBASE_DATABASE_URL = 'https://hatch-network-website-default-rtdb.europe-west1.firebasedatabase.app'
FIREBASE_SERVICE_ACCOUNT_PATH = 'firebase-service-account.json'  # Path to your service account JSON

# Library names to track (adjust to match your library names)
MOVIE_LIBRARY_NAME = 'Movies'
TV_LIBRARY_NAME = 'TV Shows'

# ========================================
# MAIN SCRIPT
# ========================================

def get_plex_stats():
    """Query Plex API and return library counts"""
    try:
        print("[Plex] Connecting to Plex server...")
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)

        # Get library counts
        movies_count = 0
        tv_shows_count = 0

        for section in plex.library.sections():
            if section.title == MOVIE_LIBRARY_NAME and section.type == 'movie':
                movies_count = len(section.all())
                print(f"[Plex] Found {movies_count} movies in '{MOVIE_LIBRARY_NAME}'")
            elif section.title == TV_LIBRARY_NAME and section.type == 'show':
                tv_shows_count = len(section.all())
                print(f"[Plex] Found {tv_shows_count} TV shows in '{TV_LIBRARY_NAME}'")

        return {
            'movies': movies_count,
            'tvShows': tv_shows_count
        }

    except Exception as e:
        print(f"[Plex] Error querying Plex: {e}")
        sys.exit(1)

def update_firebase(stats):
    """Update Firebase with Plex stats"""
    try:
        print("[Firebase] Initializing Firebase...")

        # Check if Firebase app is already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DATABASE_URL
            })

        # Update stats in Firebase
        ref = db.reference('plexStats')
        ref.set(stats)

        print(f"[Firebase] Successfully updated stats: {stats}")

    except Exception as e:
        print(f"[Firebase] Error updating Firebase: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("=" * 50)
    print("Plex Library Stats Updater")
    print("=" * 50)

    # Get Plex stats
    stats = get_plex_stats()

    # Update Firebase
    update_firebase(stats)

    print("[Success] Stats updated successfully!")
    print("=" * 50)

if __name__ == "__main__":
    main()
