# Project 3 — Identity Automation and Posture Audit

Scaffolding stage only: certificate auth via Key Vault, a Graph client
wrapper (pagination + 429 throttling), and one audit check (users without
MFA registered) — plus self-checks for all of it. The other 6 audit
checks, the HTML report, email, scheduling, and Part B write paths are not
built yet — see `REQUIREMENTS_CHECKLIST.md` and `DECISIONS.md` for what's
in/out of scope and why.

## Permissions

| Permission | Type | Granted? | Why |
|---|---|---|---|
| `User.Read.All` | Application | Yes (admin-consented) | Lists users and their basic properties (`/users`) — used here only to prove pagination/throttling against a real endpoint. |
| `Reports.Read.All` | Application | **No — not yet added or consented** | Needed for the MFA check: `GET /reports/authenticationMethods/userRegistrationDetails` returns a per-user `isMfaRegistered` boolean in one aggregated call. Chosen over `UserAuthenticationMethod.Read.All` (which would need one call per user) per DECISIONS.md's widen-only-when-needed rule. |
| `AuditLog.Read.All` | Application | **No — not yet added or consented** | Also required for the same endpoint. Confirmed by reading the actual 403 body: with only `Reports.Read.All` granted, Graph names `AuditLog.Read.All` as also required. Not assumed. |

Before `audit_mfa.py` will actually work: App registrations > this app >
API permissions > Add a permission > Microsoft Graph > Application
permissions > add both `Reports.Read.All` and `AuditLog.Read.All`, then
**Grant admin consent**. Nothing else was widened.

## Auth model

Two separate identities, on purpose:

- **Key Vault access** — your own developer identity via `az login`
  (`AzureCliCredential`). Vault and cert names come from the
  `GRAPH_KEY_VAULT_NAME`/`GRAPH_CERT_NAME` env vars (currently
  `meridian-p3-redo-kv` / `meridian-identity-audit-2-cert` in this `.env` —
  change those values to point at a different vault or cert). Your account
  needs a Key Vault role/access policy (e.g. "Key Vault Secrets User") on
  whichever vault is configured. No app credential is ever stored on disk
  or in an env var.
- **Graph auth** — the app's own identity, via `CertificateCredential`
  built from the PFX bytes just pulled out of Key Vault (client-credentials
  flow, app-only). A Key Vault *certificate* is backed by a *secret*
  holding the full PKCS#12 bundle (cert + private key) — that's why
  `graph_auth.py` reads it through `SecretClient`, not `CertificateClient`
  (which only exposes the public cert).

In production, step 1 would be a managed identity instead of
`AzureCliCredential`, with zero other code changes.

## Setup

```bash
az login
pip install -r requirements.txt

cp .env.example .env   # then fill in real values; .env is gitignored
```

`.env` is loaded automatically (`python-dotenv`) if present; real shell env
vars, if also set, take precedence over it. To skip `.env` entirely, just
export the same variables directly (`export GRAPH_TENANT_ID=...`, or
PowerShell `$env:GRAPH_TENANT_ID = "..."`).

## Verify pagination (forced small page size)

```bash
python graph_client.py --top 5
```

With `$top=5` against a ~25-user dev tenant this must issue multiple
requests. Expected log shape:

```
INFO page 1: 5 items from /users
INFO page 2: 5 items from https://graph.microsoft.com/v1.0/users?$top=5&$select=...&$skiptoken=...
...
INFO total users fetched: 25
```

More than one `page N:` line, and a `@odata.nextLink`-shaped URL on pages
after the first, is the proof.

## Verify throttling (log evidence)

A ~25-user dev tenant essentially never gets Graph to actually return a 429
on its own. Two ways to get real evidence:

1. **Deterministic, no network** — the retry logic itself, proven against a
   fake session that returns a real 429 + `Retry-After` header:
   ```bash
   python -m unittest test_graph_client.py -v
   ```
   Look for lines like:
   ```
   429 from https://graph.microsoft.com/v1.0/users; honoring Retry-After: sleeping 17s
   ```
   and the assertions that `time.sleep` was called with exactly the
   header's value (not a fixed constant, not zero).

2. **Real 429 from Graph** — fire enough concurrent requests to trip the
   tenant's throttling:
   ```bash
   for i in $(seq 1 50); do python graph_client.py --top 1 & done; wait
   ```
   Any run that hits a real 429 will log the same
   `honoring Retry-After: sleeping Ns` line with whatever value Graph
   actually sent.

   Note: a single request retries up to 5 times (`MAX_RETRIES` in
   `graph_client.py`). If throttling persists past that, the request raises
   `RuntimeError("Exceeded 5 retries...")` instead of continuing to log
   retries.

## Run the MFA check

Once `Reports.Read.All` is added and admin-consented (see Permissions
above):

```bash
python audit_mfa.py
```

```bash
python -m unittest test_audit_mfa.py -v   # filter logic, no network required
```
