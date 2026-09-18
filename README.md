# Project 3 — Identity Automation and Posture Audit

**Part A is complete and verified against real infrastructure**: cert
auth, pagination, throttling, all 7 audit checks, permissions, the
severity-ranked HTML report, email delivery, and nightly scheduling via an
Azure Container Apps Job. Not built yet: Part B write paths. See
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
| `Mail.Send` | Application | Yes | `mailer.py`: send the report via `POST /users/{mailbox}/sendMail`. Granted in Entra, then scoped to one mailbox via an Exchange Online Application Access Policy — not tenant-wide. Two separate setup steps: the Entra permission grant, and the Exchange Online RBAC scoping. |

## Auth model

`DefaultAzureCredential` reads the certificate out of Key Vault via
`SecretClient`, since a Key Vault certificate's private key lives in its
backing secret. Locally this resolves to your own `az login` identity; in
Azure (the nightly Container Apps Job) it resolves to that job's own
system-assigned managed identity instead — same code path, no
environment-specific branching. Either identity needs the "Key Vault
Secrets User" role on the vault. The app then authenticates to Graph as
itself using `CertificateCredential` built from the fetched bytes.

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
(no network, no credential). All 7 have been run and verified against the
real tenant.

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

## Run the severity-ranked HTML report

`build_report.py` runs all 7 checks and writes one HTML file, grouped
CRITICAL / WARNING / INFO per the finding-to-tier mapping in
`DECISIONS.md`. It needs all 7 permissions in the table above.

```bash
python build_report.py --output report.html
python -m unittest test_build_report.py -v   # tier-assignment logic, no network
```

Open `report.html` in a browser. Two findings are tiered by more than
their check alone: a no-MFA user is CRITICAL instead of WARNING if they
also hold a privileged directory role (cross-referenced by Graph object
id), and a service principal credential is CRITICAL instead of WARNING if
its `endDateTime` has already passed rather than merely being within 30
days.

## Send the report by email

`build_report.py` also calls `mailer.py` after writing the HTML file. If
`GRAPH_SENDER_MAILBOX` and `GRAPH_REPORT_RECIPIENT` aren't set in `.env`,
it just logs `report_email_not_sent` and moves on -- the report still
gets written either way. This mirrors Project 1's digest mailer
(`project-1-scheduled-pipeline/pipeline.py: send_digest_email`): same
message shape, same `saveToSentItems: false`, same "skip, don't fail, if
unconfigured" behavior. What's different: Project 1 fetches its own Graph
token with a client secret; this reuses this project's own cert-based,
throttle-aware `GraphClient.post()` instead of duplicating that fetch.

`Mail.Send` is granted and scoped to one mailbox (see the permissions
table). Verified: a real report was emailed and received with correct
HTML rendering.

```bash
python -m unittest test_mailer.py -v   # message shape + skip-when-unconfigured, no network
python build_report.py --output report.html   # sends for real
```

## Running nightly in Azure

Azure Container Apps Job, cron-scheduled -- same pattern as Project 1
(`project-1-scheduled-pipeline`), which was never GitHub Actions either.
No persistent state to mount and no secrets: every run re-queries the
tenant fresh, and nothing in this project's env vars is sensitive (the
certificate never leaves Key Vault).

**Live deployment:**

| Resource | Name |
|---|---|
| Job | `meridian-p3-audit-job` |
| Resource group | `meridian-identity-audit-2-rg` |
| Container registry | `meridianp3acr` |
| Key Vault | `meridian-p3-redo-kv` |
| Schedule | `0 2 * * *` (cron) |

The job's system-assigned managed identity has `AcrPull` on
`meridianp3acr` and `Key Vault Secrets User` on `meridian-p3-redo-kv`.

**Known tradeoff:** ACR admin credentials are currently enabled as a
fallback for image pull -- managed-identity pull hit auth errors during
setup. Should be fixed and admin credentials disabled in a future session.

**Verified:** a real run was triggered, completed with status `Succeeded`,
and the report email was received.

```bash
az containerapp job start --name meridian-p3-audit-job --resource-group meridian-identity-audit-2-rg
az containerapp job execution list --name meridian-p3-audit-job --resource-group meridian-identity-audit-2-rg -o table
```
