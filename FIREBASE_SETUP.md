# Firebase Authentication Setup Guide

This guide will help you set up Firebase Authentication for secure admin access to your Hatch Network media request system.

## Why Firebase Authentication?

Your admin panel now uses **Firebase Authentication** instead of client-side password checking. This provides:

- ✅ **Server-side validation** - Authentication happens on Firebase servers
- ✅ **Secure password storage** - Passwords are hashed and stored securely
- ✅ **Real user accounts** - Proper admin user management
- ✅ **Better security** - No way to bypass authentication from client-side
- ✅ **Firebase Security Rules** - Database-level access control

---

## Step 1: Enable Firebase Authentication

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **hatch-network-website**
3. Click **Authentication** in the left sidebar
4. Click **Get Started** (if not already enabled)
5. Go to **Sign-in method** tab
6. Click **Email/Password**
7. Enable **Email/Password** (toggle it ON)
8. Click **Save**

---

## Step 2: Create an Admin User

### Option A: Using Firebase Console (Recommended)

1. In Firebase Console → **Authentication**
2. Click the **Users** tab
3. Click **Add user**
4. Enter your admin email (e.g., `admin@hatchnetwork.ch`)
5. Enter a strong password
6. Click **Add user**

### Option B: Using the Website (First-Time Setup)

You can create the admin account programmatically:

1. Temporarily add this code to your browser console on the website:
```javascript
firebase.auth().createUserWithEmailAndPassword('admin@hatchnetwork.ch', 'YourStrongPassword123!')
  .then(() => console.log('Admin account created!'))
  .catch(err => console.error(err));
```

2. After creating the account, **disable new user registration** in Firebase Console:
   - Go to Authentication → Settings
   - Disable any sign-up methods you don't want

---

## Step 3: Configure Firebase Security Rules

To secure your database and prevent unauthorized access, update your Firebase Realtime Database Rules:

1. Go to Firebase Console → **Realtime Database**
2. Click the **Rules** tab
3. Replace the rules with the following:

```json
{
  "rules": {
    "requests": {
      ".read": true,
      ".write": "auth != null",
      "$requestId": {
        ".read": true,
        ".write": "auth != null",
        ".validate": "newData.hasChildren(['requesterName', 'type', 'title', 'status', 'timestamp'])"
      }
    }
  }
}
```

### What these rules do:

- ✅ **Anyone can READ** requests (needed for public viewing)
- ✅ **Only authenticated users can WRITE** (create, update, delete)
- ✅ **Data validation** ensures requests have required fields
- ✅ **Prevents anonymous users** from modifying data

4. Click **Publish** to apply the rules

---

## Step 4: Test Your Setup

1. Visit your website
2. Click the **ADMIN MODE** button (bottom-right)
3. Enter your admin email and password
4. Click **LOGIN**

If successful:
- ✅ The modal closes
- ✅ "ADMIN ACTIVE" badge appears in the header
- ✅ Admin controls appear on each request
- ✅ You can now change statuses and delete requests

---

## Step 5: Using Admin Mode

### Signing In

1. Click **ADMIN MODE** button
2. Enter your admin credentials
3. You'll remain signed in until you click **ADMIN MODE** again to sign out

### Admin Capabilities

When signed in, you can:
- **Change Status**: Click → PENDING, → IN PROGRESS, or → COMPLETED
- **Delete Requests**: Click ✕ DELETE (with confirmation)
- **View Completion Dates**: See when requests were marked complete
- **Auto-Cleanup**: Completed requests are automatically deleted after 7 days

### Signing Out

- Click the **ADMIN MODE** button again
- Your session ends immediately
- Admin controls disappear from all requests

---

## Security Best Practices

### 1. Use a Strong Password

Your admin password should:
- Be at least 12 characters long
- Include uppercase, lowercase, numbers, and symbols
- Not be reused from other accounts
- Example: `H@tch2024!Secur3`

### 2. Limit Admin Access

- Only create admin accounts for trusted users
- Don't share admin credentials
- Review the Users list in Firebase Console periodically

### 3. Monitor Activity

Firebase provides authentication logs:
- Go to Firebase Console → Authentication → Usage
- Check for unusual sign-in attempts
- Review the Activity log

### 4. Enable Two-Factor Authentication (Optional)

For maximum security:
1. Use Firebase Identity Platform (upgraded tier)
2. Enable multi-factor authentication
3. Require SMS or TOTP codes for admin sign-in

---

## Troubleshooting

### "Authentication failed" error

**Problem**: Can't sign in with your credentials

**Solutions**:
- Verify email is correct (check Firebase Console → Users)
- Try resetting password in Firebase Console
- Check browser console (F12) for detailed error messages
- Ensure Email/Password authentication is enabled

### Admin controls not appearing

**Problem**: Signed in but can't see admin buttons

**Solutions**:
- Check browser console for errors
- Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)
- Verify you're signed in: Look for "ADMIN ACTIVE" badge
- Check that `auth.onAuthStateChanged` is working (see console logs)

### Can't modify requests (Permission denied)

**Problem**: Firebase throws permission errors

**Solutions**:
- Verify Firebase Security Rules are correctly set
- Ensure you're signed in (check Firebase Console → Authentication → Users)
- Check the Rules tab shows `.write: "auth != null"`
- Test rules using Firebase Console → Rules → Simulator

### "Too many attempts" error

**Problem**: Locked out after multiple failed sign-ins

**Solutions**:
- Wait 15-30 minutes before trying again
- Reset your password in Firebase Console
- Check for caps lock or keyboard layout issues

---

## Advanced: Multiple Admin Users

To add more administrators:

1. Create additional users in Firebase Console
2. (Optional) Use Firebase custom claims for role-based access:

```javascript
// Run in Firebase Functions or Admin SDK
admin.auth().setCustomUserClaims(uid, { admin: true });
```

3. Update Security Rules to check claims:

```json
{
  "rules": {
    "requests": {
      ".write": "auth.token.admin == true"
    }
  }
}
```

---

## Migration Notes

### What Changed?

**Before (Hash-based)**:
- Password stored as SHA-256 hash in client code
- Client-side comparison only
- Could be bypassed with JavaScript modification

**After (Firebase Auth)**:
- Real authentication with Firebase
- Server-side validation
- Database-level security rules
- Proper session management

### No Action Required

The website will work immediately after you:
1. Enable Firebase Authentication
2. Create an admin user
3. Update Security Rules

Your existing requests and data are unaffected.

---

## Need Help?

- **Firebase Documentation**: https://firebase.google.com/docs/auth
- **Security Rules Guide**: https://firebase.google.com/docs/database/security
- **Firebase Console**: https://console.firebase.google.com/

For issues with your Hatch Network website, check the browser console (F12) for error messages.
