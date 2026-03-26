# ssp-test-ric

## Firebase Realtime Database Security

The multiplayer game (`tresette_multiplayers.html`) uses Firebase Realtime Database. The security rules are defined in [`database.rules.json`](database.rules.json) and replace the insecure "test mode" defaults (which allowed anyone to read and write the entire database).

### What the rules do

| Path | Read | Write |
|------|------|-------|
| `lobby/{roomCode}` | ✅ Anyone | ✅ Validated (host ≤ 50 chars, label ≤ 100 chars) |
| `rooms/{roomCode}/state` | ✅ Anyone | ✅ Anyone (host-controlled) |
| `rooms/{roomCode}/messages/{id}` | ✅ Anyone | ✅ Validated (_from ≤ 50 chars, t ≤ 20 chars) |
| `rooms/{roomCode}/seats/{playerId}` | ✅ Anyone | ✅ Validated (must be a number) |
| All other paths | ❌ Denied | ❌ Denied |

### Deploying the rules

1. Install the Firebase CLI: `npm install -g firebase-tools`
2. Log in: `firebase login`
3. Deploy the rules: `firebase deploy --only database`

### Firebase API key note

The Firebase **web API key** in `tresette_multiplayers.html` is intentionally public — it is a project identifier required by the Firebase client SDK, not a secret credential. Real access control is enforced by the security rules above.

To further restrict the API key to your own domain only, go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials), select the API key, and add your domain under **Application restrictions → HTTP referrers**.