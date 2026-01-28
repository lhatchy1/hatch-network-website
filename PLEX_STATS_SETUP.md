# Plex Library Stats Setup Guide (Windows Server 2019)

This guide will help you set up automatic Plex library stats updates on your website.

## Overview

The system works by:
1. A Python script queries your Plex server for library counts
2. Updates Firebase Realtime Database with the counts
3. Your website displays the cached data from Firebase
4. Windows Task Scheduler runs the script every 30 minutes to keep stats updated

---

## Prerequisites

- Python 3.6 or higher installed on Windows Server 2019
- Access to your Plex server (local or remote)
- Firebase project with service account credentials
- Administrator access to set up Task Scheduler

---

## Step 1: Install Python on Windows Server 2019

If Python isn't already installed:

1. Download Python from [python.org](https://www.python.org/downloads/)
   - Get Python 3.11 or later (recommended)
2. Run the installer
3. **Important**: Check ✅ "Add Python to PATH" during installation
4. Click "Install Now"

### Verify Installation

Open PowerShell and run:
```powershell
python --version
```

You should see something like `Python 3.11.x`

---

## Step 2: Get Your Plex Token

You need a Plex authentication token to access the API.

### Method 1: Via Plex Web App (Easiest)
1. Open Plex Web App in your browser (http://localhost:32400/web)
2. Play any media item
3. Click the **ⓘ** (info) button or **⋮** (three dots) menu
4. Click **"View XML"** or **"Get Info"**
5. Look at the URL in the address bar
6. Find `X-Plex-Token=xxxxx` in the URL
7. Copy the token (everything after `X-Plex-Token=`)

### Method 2: Via Settings
1. Sign in to Plex Web App
2. Go to Settings → Account → Privacy
3. Scroll to the bottom, you'll see your authentication token
4. Click "Show" to reveal it

### Method 3: Via PowerShell
```powershell
$credentials = "your-plex-username:your-plex-password"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($credentials)
$encodedCreds = [System.Convert]::ToBase64String($bytes)

Invoke-WebRequest -Uri "https://plex.tv/users/sign_in.xml" `
  -Method POST `
  -Headers @{"Authorization"="Basic $encodedCreds"}
```
Look for `<authentication-token>` in the response.

---

## Step 3: Get Firebase Service Account Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (`hatch-network-website`)
3. Click the **⚙️ Settings** icon → **Project settings**
4. Go to **Service accounts** tab
5. Click **"Generate new private key"**
6. Save the JSON file as `firebase-service-account.json`
7. **Keep this file secure** - it grants full access to your Firebase project

---

## Step 4: Set Up the Script

### 4.1 Create a Directory

Open PowerShell as Administrator:

```powershell
# Create directory for the script
New-Item -ItemType Directory -Path "C:\PlexStats" -Force
cd C:\PlexStats
```

### 4.2 Copy Files

1. Download `update_plex_stats.py` from your repository to `C:\PlexStats\`
2. Copy `firebase-service-account.json` to `C:\PlexStats\`

You can use PowerShell to download:
```powershell
# Example if files are in a shared location or USB drive
Copy-Item "D:\update_plex_stats.py" -Destination "C:\PlexStats\"
Copy-Item "D:\firebase-service-account.json" -Destination "C:\PlexStats\"
```

### 4.3 Install Python Dependencies

Open PowerShell in `C:\PlexStats`:

```powershell
# Install required packages
pip install plexapi firebase-admin
```

If you get "pip not found", try:
```powershell
python -m pip install plexapi firebase-admin
```

---

## Step 5: Configure the Script

Edit `C:\PlexStats\update_plex_stats.py` using Notepad or any text editor:

```powershell
notepad C:\PlexStats\update_plex_stats.py
```

Update these values:

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

### Finding Your Exact Library Names

Run this in PowerShell to see your library names:

```powershell
cd C:\PlexStats
python -c "from plexapi.server import PlexServer; plex = PlexServer('http://localhost:32400', 'YOUR_TOKEN_HERE'); print([s.title for s in plex.library.sections()])"
```

**Important**: Library names are case-sensitive. If your libraries are named "movies" and "tv", update the script accordingly.

---

## Step 6: Test the Script

Before setting up automation, test that it works:

```powershell
cd C:\PlexStats
python update_plex_stats.py
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

### Common Errors and Fixes

**"Unauthorized"**:
- Check your Plex token is correct
- Ensure no extra spaces when copying the token

**"Connection refused"**:
- Check Plex Media Server is running
- Verify PLEX_URL (try `http://127.0.0.1:32400` if localhost doesn't work)

**"No module named 'plexapi'"**:
```powershell
pip install plexapi firebase-admin
```

**"Permission denied" (Firebase)**:
- Check `firebase-service-account.json` is in the same folder
- Verify the JSON file is valid

**Library not found**:
- Run the library name checker command above
- Update MOVIE_LIBRARY_NAME and TV_LIBRARY_NAME to match exactly

---

## Step 7: Set Up Windows Task Scheduler

Now automate the script to run every 30 minutes.

### Method 1: Task Scheduler GUI (Easier)

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Or search "Task Scheduler" in Start menu

2. **Create New Task**:
   - In the right panel, click **"Create Task"** (not "Create Basic Task")

3. **General Tab**:
   - **Name**: `Plex Stats Updater`
   - **Description**: `Updates Plex library statistics in Firebase every 30 minutes`
   - ✅ **Run whether user is logged on or not**
   - ✅ **Run with highest privileges**
   - **Configure for**: Windows Server 2019

4. **Triggers Tab**:
   - Click **"New..."**
   - **Begin the task**: On a schedule
   - **Settings**: Daily
   - **Recur every**: 1 days
   - ✅ **Repeat task every**: 30 minutes
   - **for a duration of**: Indefinitely
   - ✅ **Enabled**
   - Click **OK**

5. **Actions Tab**:
   - Click **"New..."**
   - **Action**: Start a program
   - **Program/script**: `C:\Python311\python.exe` (adjust to your Python path)
     - To find Python path: `where python` in PowerShell
   - **Add arguments**: `update_plex_stats.py`
   - **Start in**: `C:\PlexStats`
   - Click **OK**

6. **Conditions Tab**:
   - ⬜ **Uncheck** "Start the task only if the computer is on AC power"
   - ⬜ **Uncheck** "Stop if the computer switches to battery power"

7. **Settings Tab**:
   - ✅ **Allow task to be run on demand**
   - ✅ **Run task as soon as possible after a scheduled start is missed**
   - ✅ **If the task fails, restart every**: 5 minutes (attempt 3 times)
   - **If the running task does not end when requested**: Stop the existing instance

8. **Save**:
   - Click **OK**
   - Enter your Windows administrator password when prompted

### Method 2: PowerShell (Advanced)

Run this in PowerShell as Administrator:

```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Python311\python.exe' `
    -Argument 'update_plex_stats.py' `
    -WorkingDirectory 'C:\PlexStats'

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" `
    -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "Plex Stats Updater" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Updates Plex library statistics in Firebase every 30 minutes"
```

### Verify Task is Scheduled

In Task Scheduler:
1. Navigate to **Task Scheduler Library**
2. Find **"Plex Stats Updater"**
3. Right-click → **Run** to test immediately
4. Check **Last Run Result** column - should show "The operation completed successfully (0x0)"

### View Task Logs

To see if the task ran successfully:
1. In Task Scheduler, click on your task
2. Go to **History** tab at the bottom
3. Look for "Task completed" events

---

## Step 8: Set Up Logging (Optional but Recommended)

Modify the scheduled task to log output:

### Update the Action:

**Program/script**: `cmd.exe`

**Add arguments**:
```
/c "C:\Python311\python.exe C:\PlexStats\update_plex_stats.py >> C:\PlexStats\plex-stats.log 2>&1"
```

Now you can check `C:\PlexStats\plex-stats.log` to see script output and debug issues.

To view logs in PowerShell:
```powershell
Get-Content C:\PlexStats\plex-stats.log -Tail 50
```

---

## Step 9: Update Firebase Security Rules

Add read access for Plex stats to your Firebase Security Rules:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Realtime Database** → **Rules**
4. Add this to your rules:

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

5. Click **Publish**

This allows anyone to read stats (for display on website) but only the service account can write.

---

## Verification

1. Wait 30 minutes for the task to run (or run it manually in Task Scheduler)
2. Visit your website
3. You should see the movie and TV show counts displayed at the top
4. Check browser console (F12) for any errors

### Manual Check

In PowerShell:
```powershell
# Check if task exists
Get-ScheduledTask -TaskName "Plex Stats Updater"

# Check task history
Get-ScheduledTask -TaskName "Plex Stats Updater" | Get-ScheduledTaskInfo

# Run task manually
Start-ScheduledTask -TaskName "Plex Stats Updater"
```

---

## Troubleshooting

### Stats show "--" on website
1. Check Firebase Realtime Database → Data tab → Look for `plexStats` node
2. Verify the script ran successfully:
   ```powershell
   Get-Content C:\PlexStats\plex-stats.log -Tail 20
   ```
3. Check browser console (F12) for JavaScript errors

### Task Scheduler shows "The operator or administrator has refused the request (0x800710E0)"
- Run Task Scheduler as Administrator
- Recreate the task with "Run with highest privileges" checked

### Script runs manually but not via Task Scheduler
- **Problem**: Environment variables or paths differ when running as SYSTEM
- **Solution**: Use absolute paths in script:
  ```python
  FIREBASE_SERVICE_ACCOUNT_PATH = r'C:\PlexStats\firebase-service-account.json'
  ```

### Python not found in Task Scheduler
- Find Python path: `where python` in PowerShell
- Use full path like `C:\Users\YourUser\AppData\Local\Programs\Python\Python311\python.exe`
- Or use Python Launcher: `py -3` instead of `python`

### Permission errors
- Ensure Task runs as Administrator or SYSTEM account
- Check file permissions on `C:\PlexStats` folder:
  ```powershell
  icacls C:\PlexStats
  ```

### Firewall blocking Firebase connection
- Windows Firewall might block Python
- Add firewall rule:
  ```powershell
  New-NetFirewallRule -DisplayName "Python" -Direction Outbound -Program "C:\Python311\python.exe" -Action Allow
  ```

---

## Security Notes

⚠️ **Important Security Practices:**

1. **Protect sensitive files**:
   ```powershell
   # Restrict access to firebase-service-account.json
   icacls "C:\PlexStats\firebase-service-account.json" /inheritance:r
   icacls "C:\PlexStats\firebase-service-account.json" /grant:r "SYSTEM:(R)"
   icacls "C:\PlexStats\firebase-service-account.json" /grant:r "Administrators:(R)"
   ```

2. **Never commit** `firebase-service-account.json` to git
3. **Never expose** your Plex token publicly
4. Consider using environment variables:
   - In Windows, set via System Properties → Environment Variables
   - In script: `PLEX_TOKEN = os.environ.get('PLEX_TOKEN', '')`

5. **Backup your credentials**:
   ```powershell
   Copy-Item C:\PlexStats\firebase-service-account.json -Destination "D:\Backup\"
   ```

---

## Alternative: Run as Windows Service

For a more robust solution, you can create a Windows Service that runs continuously:

1. Install NSSM (Non-Sucking Service Manager):
   ```powershell
   # Download from https://nssm.cc/download
   ```

2. Create service:
   ```powershell
   nssm install PlexStatsUpdater "C:\Python311\python.exe" "C:\PlexStats\update_plex_stats.py"
   nssm set PlexStatsUpdater AppDirectory "C:\PlexStats"
   nssm set PlexStatsUpdater DisplayName "Plex Stats Updater Service"
   nssm set PlexStatsUpdater Description "Updates Plex library statistics every 30 minutes"
   nssm start PlexStatsUpdater
   ```

However, you'd need to modify the script to run in a loop with sleep intervals.

---

## Linux/Mac Instructions (Alternative)

<details>
<summary>Click to expand Linux/Mac instructions</summary>

### Install Dependencies
```bash
pip3 install plexapi firebase-admin
```

### Set Up Cron Job
```bash
# Make script executable
chmod +x /path/to/update_plex_stats.py

# Edit crontab
crontab -e

# Add this line (runs every 30 minutes)
*/30 * * * * cd /path/to/hatch-network-website && /usr/bin/python3 update_plex_stats.py >> /var/log/plex-stats.log 2>&1
```

### Verify Cron Job
```bash
crontab -l
grep CRON /var/log/syslog
```

</details>

---

## Summary

Once set up, your website will automatically display:
- 🎬 Total number of movies in your Plex library
- 📺 Total number of TV shows in your Plex library

Stats update every 30 minutes automatically via Windows Task Scheduler!

## Quick Reference

**Script location**: `C:\PlexStats\update_plex_stats.py`
**Log file**: `C:\PlexStats\plex-stats.log`
**Task name**: Plex Stats Updater
**Run frequency**: Every 30 minutes

**Manual commands**:
```powershell
# Test script
cd C:\PlexStats
python update_plex_stats.py

# View logs
Get-Content C:\PlexStats\plex-stats.log -Tail 20

# Run task now
Start-ScheduledTask -TaskName "Plex Stats Updater"

# Check task status
Get-ScheduledTask -TaskName "Plex Stats Updater" | Get-ScheduledTaskInfo
```
