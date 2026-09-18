# Project 3 — Identity Automation and Posture Audit

Scaffolding stage: certificate auth via Key Vault, a Graph client wrapper
(pagination + 429 throttling), one audit check (users without MFA
registered), and self-checks for all of it. Not built yet: the other 6
audit checks, the HTML report, email, scheduling, and Part B write paths.
See `REQUIREMENTS_CHECKLIST.md` and `DECISIONS.md` for scope.

## Permissions

| Permission | Type | Granted? | Why |
|---|---|---|---|
| `User.Read.All` | Application | Yes | Lists users (`/users`) for the pagination/throttling demo. |
| `Reports.Read.All` | Application | No | Needed for `GET /reports/authenticationMethods/userRegistrationDetails`, the MFA check's data source. |
| `AuditLog.Read.All` | Application | No | Also required by that same endpoint. |

To use `audit_mfa.py`: App registrations > this app > API permissions > Add
a permission > Microsoft Graph > Application permissions > add
`Reports.Read.All` and `AuditLog.Read.All`, then grant admin consent.

## Auth model

Your own identity (`az login` / `AzureCliCredential`) reads the
certificate out of Key Vault via `SecretClient`, since a Key Vault
certificate's private key lives in its backing secret. The app then
authenticates to Graph as itself using `CertificateCredential` built from
those bytes. In production, swap the Key Vault identity for a managed
identity.

## Setup

```bash
az login
pip install -r requirements.txt

cp .env.example .env   # fill in real values; .env is gitignored
```

`.env` loads automatically via `python-dotenv`. Shell env vars, if set,
take precedence.

## Verify pagination

```bash
python graph_client.py --top 5
```

Against a ~25-user tenant this issues multiple requests. Look for more
than one `page N:` log line, with later pages' URLs containing
`$skiptoken`.

## Verify throttling

```bash
python -m unittest test_graph_client.py -v
```

Proves the retry logic against a fake 429 + `Retry-After` response. Look
for `honoring Retry-After: sleeping Ns` in the output.

To trigger a real 429:

```bash
for i in $(seq 1 50); do python graph_client.py --top 1 & done; wait
```

A single request retries up to 5 times (`MAX_RETRIES`). Past that it
raises instead of continuing to retry.

## Run the MFA check

Once both permissions above are granted and consented:

```bash
python audit_mfa.py
python -m unittest test_audit_mfa.py -v   # filter logic, no network
```
