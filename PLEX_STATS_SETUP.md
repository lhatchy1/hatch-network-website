# Plex Library Stats Setup Guide

This guide will help you set up automatic Plex library stats updates on your website.

## Overview

The system works by:
1. A Python script queries your Plex server for library counts
2. Updates Firebase Realtime Database with the counts
3. Your website displays the cached data from Firebase
4. A cron job runs the script every 30 minutes to keep stats updated

---

## Prerequisites

- Python 3.6 or higher installed on your Plex server
- Access to your Plex server (local or remote)
- Firebase project with service account credentials

---

## Step 1: Get Your Plex Token

You need a Plex authentication token to access the API.

### Method 1: Via Plex Web App
1. Open Plex Web App in your browser
2. Play any media item
3. Click the **ⓘ** (info) button or **⋮** (three dots) menu
4. Click **"View XML"** or **"Get Info"**
5. Look at the URL in the address bar
6. Find `X-Plex-Token=xxxxx` in the URL
7. Copy the token (everything after `X-Plex-Token=`)

### Method 2: Via Settings
1. Sign in to Plex Web App
2. Go to Settings → Account → Privacy
3. At the bottom, you'll see your authentication token

### Method 3: Via Command Line
```bash
curl -u 'your-plex-username:your-plex-password' \
  'https://plex.tv/users/sign_in.xml' -X POST
```
Look for `<authentication-token>` in the XML response.

---

## Step 2: Get Firebase Service Account Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (`hatch-network-website`)
3. Click the **⚙️ Settings** icon → **Project settings**
4. Go to **Service accounts** tab
5. Click **"Generate new private key"**
6. Save the JSON file as `firebase-service-account.json`
7. **Keep this file secure** - it grants full access to your Firebase project

---

## Step 3: Install Python Dependencies

On your Plex server machine, install the required Python packages:

```bash
# Install pip if you don't have it
python3 -m ensurepip --upgrade

# Install required packages
pip3 install plexapi firebase-admin
```

---

## Step 4: Configure the Script

1. Copy `update_plex_stats.py` to your Plex server
2. Copy `firebase-service-account.json` to the same directory
3. Edit `update_plex_stats.py` and update these values:

```python
# Plex Server Configuration
PLEX_URL = 'http://localhost:32400'  # Change if Plex is on different port/host
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'  # Paste your token here

# Firebase Configuration (these should be correct already)
FIREBASE_DATABASE_URL = 'https://hatch-network-website-default-rtdb.europe-west1.firebasedatabase.app'
FIREBASE_SERVICE_ACCOUNT_PATH = 'firebase-service-account.json'

# Library names (adjust to match YOUR library names exactly)
MOVIE_LIBRARY_NAME = 'Movies'
TV_LIBRARY_NAME = 'TV Shows'
```

### Finding Your Library Names

Run this command to see your exact library names:

```bash
python3 -c "from plexapi.server import PlexServer; \
  plex = PlexServer('http://localhost:32400', 'YOUR_TOKEN'); \
  print([s.title for s in plex.library.sections()])"
```

---

## Step 5: Test the Script

Run the script manually to verify it works:

```bash
python3 update_plex_stats.py
```

**Expected output:**
```
==================================================
Plex Library Stats Updater
==================================================
[Plex] Connecting to Plex server...
[Plex] Found 1234 movies in 'Movies'
[Plex] Found 567 TV shows in 'TV Shows'
[Firebase] Initializing Firebase...
[Firebase] Successfully updated stats: {'movies': 1234, 'tvShows': 567}
[Success] Stats updated successfully!
==================================================
```

If you see errors:
- **"Unauthorized"**: Check your Plex token
- **"Connection refused"**: Check PLEX_URL and ensure Plex is running
- **"Permission denied"**: Check Firebase service account credentials
- **Library not found**: Check MOVIE_LIBRARY_NAME and TV_LIBRARY_NAME match exactly

---

## Step 6: Set Up Cron Job (Linux/Mac)

To automatically update stats every 30 minutes:

1. Make the script executable:
```bash
chmod +x /path/to/update_plex_stats.py
```

2. Edit your crontab:
```bash
crontab -e
```

3. Add this line (update the path to match your setup):
```bash
*/30 * * * * cd /path/to/hatch-network-website && /usr/bin/python3 update_plex_stats.py >> /var/log/plex-stats.log 2>&1
```

This runs every 30 minutes and logs output to `/var/log/plex-stats.log`.

### Cron Schedule Examples:
```bash
*/30 * * * *    # Every 30 minutes
0 * * * *       # Every hour
0 */2 * * *     # Every 2 hours
0 0 * * *       # Once per day at midnight
```

4. Verify cron job is registered:
```bash
crontab -l
```

---

## Step 6 Alternative: Windows Task Scheduler

If your Plex server runs on Windows:

1. Open **Task Scheduler**
2. Create New Task:
   - **General**: Name it "Plex Stats Updater"
   - **Triggers**: New → Repeat task every 30 minutes
   - **Actions**:
     - Program: `C:\Python3\python.exe`
     - Arguments: `C:\path\to\update_plex_stats.py`
     - Start in: `C:\path\to\hatch-network-website`
   - **Conditions**: Uncheck "Start only if on AC power"
   - **Settings**: Check "Run task as soon as possible after scheduled start is missed"

---

## Step 7: Update Firebase Security Rules

Add read access for Plex stats to your Firebase Security Rules:

```json
{
  "rules": {
    "plexStats": {
      ".read": true,
      ".write": false
    },
    "requests": {
      // ... existing rules ...
    }
  }
}
```

This allows anyone to read stats (for display on website) but only the service account can write.

---

## Verification

1. Wait a few minutes after running the script
2. Visit your website at https://hatch-network-website.web.app
3. You should see the movie and TV show counts displayed at the top
4. Check browser console (F12) for any errors

---

## Troubleshooting

### Stats show "--" on website
- Check Firebase Realtime Database → Data tab → Look for `plexStats` node
- Verify the script ran successfully (check logs)
- Check browser console for JavaScript errors

### Script fails with "Module not found"
```bash
pip3 install --upgrade plexapi firebase-admin
```

### Permission errors on Firebase
- Verify `firebase-service-account.json` is correct
- Check Firebase Security Rules allow writing to `/plexStats`

### Cron job not running
```bash
# Check cron service is running
sudo systemctl status cron  # Linux
sudo systemctl start cron   # Start if stopped

# Check system logs
grep CRON /var/log/syslog
```

---

## Optional: Run as Systemd Service (Linux)

For more robust scheduling, create a systemd timer:

1. Create `/etc/systemd/system/plex-stats.service`:
```ini
[Unit]
Description=Update Plex Stats
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/hatch-network-website
ExecStart=/usr/bin/python3 /path/to/hatch-network-website/update_plex_stats.py
```

2. Create `/etc/systemd/system/plex-stats.timer`:
```ini
[Unit]
Description=Run Plex Stats Updater every 30 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable plex-stats.timer
sudo systemctl start plex-stats.timer
sudo systemctl status plex-stats.timer
```

---

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit** `firebase-service-account.json` to git
2. **Never expose** your Plex token publicly
3. Keep file permissions restrictive:
   ```bash
   chmod 600 firebase-service-account.json
   chmod 600 update_plex_stats.py  # if it contains the token
   ```
4. Consider using environment variables for sensitive data:
   ```python
   PLEX_TOKEN = os.environ.get('PLEX_TOKEN', 'fallback-token')
   ```

---

## Support

If you encounter issues:
1. Check the script logs
2. Verify Plex server is accessible
3. Test Firebase connectivity
4. Check Firebase Security Rules
5. Review browser console for errors

---

## Summary

Once set up, your website will automatically display:
- 🎬 Total number of movies in your Plex library
- 📺 Total number of TV shows in your Plex library

Stats update every 30 minutes automatically!
