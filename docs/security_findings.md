# Security Findings
_Generated: 2026-04-29_

---

## Critical — Fix Immediately

### 1. No .gitignore (FIXED in Phase 2)
**Status:** FIXED — `.gitignore` created in Phase 2 covering `.env` and `schwab_token.json`.

**Was:** No `.gitignore` existed in the repo. A single `git add .` or `git init && git add .`
would have committed both secret files.

---

## Active Risks

### 2. `.env` — Contains Live API Credentials
**File:** `.env`
**Contents:** SCHWAB_API_KEY, SCHWAB_APP_SECRET, TRADOVATE_API_KEY, TRADOVATE_API_SECRET,
TRADOVATE_APP_ID, TRADOVATE_APP_VERSION, TRADOVATE_DEMO
**Risk level:** HIGH — Schwab key + secret grants API access to the brokerage account.
**Mitigation:**
- Now covered by `.gitignore` — will not be committed going forward.
- For AWS: these credentials should move to Secrets Manager and be removed from `.env` entirely.
- Rotate the Schwab API key if there is any reason to believe this repo was previously committed
  to a remote without a .gitignore.

### 3. `schwab_token.json` — Live OAuth Token
**File:** `schwab_token.json`
**Contents:** Access token + refresh token for the Schwab API session.
**Risk level:** HIGH — this token can be used to pull real-time market data from the account.
**Mitigation:**
- Now covered by `.gitignore`.
- Token auto-refreshes and expires ~7 days (refresh token). If compromised, re-run `auth_schwab.py`
  to generate a new token (old one will be invalidated on next refresh).
- On Lambda, token is stored in a private S3 bucket — not in this repo.

---

## No Issues Found

- **No hardcoded secrets in .py files** — all credentials go through `os.getenv()` / dotenv.
- **No credentials in documentation files** — CLAUDE.md, LOGIC.md, essay files contain no keys.
- **No credentials in backtest CSVs** — output files contain only trade data.
- **No credentials in requirements.txt or pyproject.toml**.

---

## Recommendations

1. **Rotate Schwab API key** if there is any chance this directory was ever pushed to a remote
   repo or cloud sync (OneDrive, Dropbox, iCloud) that could have exposed `.env`.
2. **Move to Secrets Manager** when the AWS deployment is the primary runner. Remove Schwab
   credentials from `.env` and use the Lambda Secrets Manager path for local dev too
   (or keep them in `.env` only — never commit).
3. **Add pre-commit hook** to scan for secrets patterns before any commit. Tool: `detect-secrets`
   or `truffleHog`.
4. **Audit cloud sync** — if this Desktop folder syncs to OneDrive or similar, `.env` may already
   be in the cloud. Check and restrict sync if needed.
