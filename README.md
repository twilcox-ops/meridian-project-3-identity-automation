# Project 3 — Identity Automation and Posture Audit

Certificate auth via Key Vault, a Graph client wrapper (pagination + 429
throttling), and all 7 Part A audit checks with self-checks for each. Not
built yet: the HTML report, email, scheduling, and Part B write paths. See
`REQUIREMENTS_CHECKLIST.md` and `DECISIONS.md` for scope.

## Permissions

| Permission | Type | Granted? | Why |
|---|---|---|---|
| `User.Read.All` | Application | Yes | Lists users (`/users`) for the pagination/throttling demo, stale-licensed and guest-tenure checks. |
| `Reports.Read.All` | Application | Yes | Needed for `GET /reports/authenticationMethods/userRegistrationDetails`, the MFA check's data source. |
| `AuditLog.Read.All` | Application | Yes | Also required by that same endpoint, and by reading `signInActivity` for the stale-licensed check. |
| `RoleManagement.Read.Directory` | Application | Yes | `audit_privileged_roles.py`: list `/directoryRoles` and their members. |
| `Application.Read.All` | Application | Yes | `audit_sp_creds.py`: read `/servicePrincipals` key/password credential expiry. |
| `Group.Read.All` | Application | Yes | `audit_ownerless_groups.py`: list `/groups` and their `/owners`. |
| `Device.Read.All` | Application | Yes | `audit_devices.py`: read `/devices` compliance and last check-in. |

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

## Run the audit checks

Each check works like the MFA one: a script that hits the tenant, and a
`test_*.py` that proves the filter/flag logic with fake Graph responses
(no network, no credential). All permissions in the table above are
granted and admin-consented; the checks besides `audit_mfa.py` and
`audit_stale_licensed.py` haven't been run against the real tenant yet.

```bash
python audit_mfa.py                          # Reports.Read.All, AuditLog.Read.All
python audit_stale_licensed.py                # User.Read.All, AuditLog.Read.All
python audit_guests.py                        # User.Read.All
python audit_privileged_roles.py              # RoleManagement.Read.Directory
python audit_sp_creds.py                      # Application.Read.All
python audit_ownerless_groups.py              # Group.Read.All
python audit_devices.py                       # Device.Read.All

python -m unittest discover -p "test_audit_*.py" -v
```
