# Requirements Checklist — Project 3: Identity Automation and Posture Audit

Extracted verbatim from `PROJECT-3-identity-automation-audit.md`. No paraphrasing. Line numbers refer to the source file.

## Setup (lines 15–23)

- [ ] "Register an app in Entra ID. Use **certificate credentials**, not a client secret" (line 21)
- [ ] "Nothing in this project should ever point at a tenant you don't own." (line 19)

## Part A — the audit (lines 29–45)

- [ ] "A nightly job producing a security posture report" (line 31)
- [ ] "Users without MFA registered" (line 33)
- [ ] "Accounts that haven't signed in for 90+ days but still hold licenses" (line 34) — AMBIGUOUS — flag for review (what counts as "signed in" — interactive sign-in, any sign-in, which log/property defines the 90-day threshold — is not specified)
- [ ] "Guest accounts and how long they've been there" (line 35)
- [ ] "Users holding privileged directory roles" (line 36)
- [ ] "Service principals with credentials nearing expiry" (line 37) — AMBIGUOUS — flag for review ("nearing expiry" threshold, e.g. number of days, is not specified)
- [ ] "Groups with no owner" (line 38)
- [ ] "Devices that are non-compliant or haven't checked in" (line 39) — AMBIGUOUS — flag for review ("haven't checked in" — no time threshold given)
- [ ] "Output an HTML report, severity-ranked, emailed on a schedule." (line 41) — AMBIGUOUS — flag for review (severity ranking scheme/tiers not defined)
- [ ] "Reuse the Project 1 scheduling and mailer patterns — that reuse is the point." (line 41–42)
- [ ] "Read-only until the audit is solid." (line 44)

## Part B — the writes (lines 47–61)

- [ ] "Create the user with a generated password" (line 51) — AMBIGUOUS — flag for review (password generation policy/complexity not specified)
- [ ] "Add to groups based on a department mapping in config" (line 52) — AMBIGUOUS — flag for review (config format/schema for the department mapping not specified)
- [ ] "Assign a license" (line 53) — AMBIGUOUS — flag for review (which license/SKU is not specified)
- [ ] "Log every action to an audit trail" (line 54)
- [ ] "the harder half — offboarding: disable sign-in, revoke refresh tokens, remove from groups, reclaim the license, convert the mailbox to shared" (line 56–57)
- [ ] "Every write path needs a `--dry-run` that is the default." (line 59)
- [ ] "The real run needs an explicit flag and a typed confirmation." (line 59–60) — AMBIGUOUS — flag for review (the exact confirmation text/mechanism is not specified)
- [ ] "Build a rollback for anything reversible." (line 61) — AMBIGUOUS — flag for review (which offboarding/onboarding actions are "reversible" is not enumerated)

## Technical requirements (lines 65–81)

- [ ] "Graph returns `@odata.nextLink`." (line 67)
- [ ] "write it correctly anyway and test with `$top=5` to force paging" (line 68)
- [ ] "Graph returns 429 with a `Retry-After` header." (line 70)
- [ ] "Honor the header — don't use a fixed sleep, and don't retry immediately." (line 71)
- [ ] "Start with `User.Read.All` and widen only where you must." (line 73) — AMBIGUOUS — flag for review (no criteria given for when widening is "must")
- [ ] "Document each permission and why." (line 74)
- [ ] "`Directory.ReadWrite.All` is the lazy answer and an interviewer will notice." (line 75–76)
- [ ] "Graph's `$batch` endpoint bundles up to 20 requests." (line 77)
- [ ] "Use it and measure the improvement." (line 78) — AMBIGUOUS — flag for review (metric/method for "measure the improvement" not specified)
- [ ] "Certificate in a vault or the OS certificate store." (line 80) — AMBIGUOUS — flag for review (two options given, no single required mechanism)

## Acceptance criteria (lines 86–92)

- [ ] Audit runs nightly, unattended, emailing a severity-ranked report
- [ ] Pagination proven against a forced small page size
- [ ] 429s handled by honoring `Retry-After`, demonstrable in logs
- [ ] Every permission listed in the README with a one-line justification
- [ ] All write operations dry-run by default
- [ ] Complete audit log: who ran it, what changed, before and after
- [ ] Offboarding is reversible where the API allows, documented where it isn't — AMBIGUOUS — flag for review ("where the API allows" is not enumerated; requires explicit per-action determination)
