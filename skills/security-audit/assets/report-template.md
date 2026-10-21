# Security & Performance Audit: <project name>

**Stack detected:** <framework · backend · auth · payments · host>
**Scope:** <what was scanned: folders, scripts run, references applied>

## Fix these first
1. **[CRITICAL] <short title>**: <one-sentence why it matters>
   - Where: `path/file.ts:42`
   - Fix: <exact change or SQL>
2. ...
(5 to 8 items max)

## All findings

### Critical
| # | Issue | Where | Why it matters | Fix |
|---|-------|-------|----------------|-----|

### High
(same table)

### Medium / Low
(same table)

*Items from automated scans that I did not confirm by reading the code are marked "needs confirmation".*

## Looks good
- <checks that passed, one line each>

## Verify in your dashboards (the repo can't prove these)
- [ ] RLS enabled on every table in the live database
- [ ] Supabase/Firebase auth: email confirmation, redirect URL allow-list, leaked-password protection
- [ ] Provider spend limits and budget alerts set (LLM, email, SMS, cloud)
- [ ] Any exposed key has been rotated, not just deleted
- [ ] API keys restricted by domain/IP/app where the provider supports it

## Not checked
- <e.g. dependency vulnerabilities (run `npm audit`), infrastructure and DNS config, anything outside the repo, load testing, business-logic flaws beyond those listed>

---
*Baseline hygiene review, not a penetration test. "No issues found" means none in the areas listed above.*
