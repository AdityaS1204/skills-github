# Firebase checklist

Firebase config (apiKey, projectId) in your frontend is normal and public. **Security rules** are what protect Firestore, Realtime Database and Storage.

## 1. Rules are not open (Critical)
Look in `firestore.rules`, `database.rules.json`, `storage.rules`:
- `allow read, write: if true;` is fully open.
- `allow read, write: if request.time < timestamp.date(...)` is the test-mode default and **expires into a locked or still-open state**; replace it.
- `allow read, write: if request.auth != null;` means any signed-in user (including anyone who just signs up) can read and write everything. Almost never enough.
- Realtime Database: `".read": true` or `".write": true` at the root.

## 2. Ownership rules
```
match /notes/{noteId} {
  allow read, update, delete: if request.auth != null && resource.data.userId == request.auth.uid;
  allow create: if request.auth != null && request.resource.data.userId == request.auth.uid;
}
```
- Check `request.resource.data` on create/update so users can't write someone else's `userId` or set `isAdmin`, `plan`, `credits`.
- Use custom claims (set server-side) for roles, never a field the user can edit.
- Validate shape and size of writes (`request.resource.data.keys().hasOnly([...])`, string length limits).

## 3. Storage
- Rules should tie paths to `request.auth.uid` (`/users/{uid}/...`) and limit `request.resource.size` and `contentType`.
- Public download URLs with tokens are effectively public forever. Avoid for private files.

## 4. Admin SDK and keys
- Firebase Admin SDK / service account JSON bypasses all rules. Server only, never in client code or the repo.
- Cloud Functions that act with admin rights must check `context.auth` / verify the ID token (`verifyIdToken`) and ownership themselves.
- Enable **App Check** to cut abuse from scripts and clones.

## 5. Abuse and billing
- Firestore has no built-in rate limit. Unbounded listeners and queries cost money; flag `onSnapshot` on large collections without `limit()`.
- Set budget alerts in Google Cloud.
- Restrict the browser API key by HTTP referrer / app bundle id in the Cloud console.

## Verify
Use the Rules Playground in the console, or the Emulator with `@firebase/rules-unit-testing`, to test as unauthenticated, user A reading user B, and user A writing a forged `userId`.
