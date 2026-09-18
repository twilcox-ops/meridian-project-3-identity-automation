# Project 3 — Business/Threshold Decisions
(spec is silent on these; decided by Tyler, not inferred by Claude Code)

- Stale account threshold: 90+ days since last interactive sign-in (signInActivity.lastSignInDateTime)
- Service principal credential "nearing expiry": 30 days
- Device "haven't checked in": 90 days
- Severity ranking: 3-tier — CRITICAL / WARNING / INFO

  Finding-to-tier mapping:
  - No MFA, privileged-role user: CRITICAL
  - No MFA, regular user: WARNING
  - Stale + licensed account: WARNING
  - Ownerless group: WARNING
  - Privileged role holder (informational): INFO
  - SP credential already expired: CRITICAL
  - SP credential expiring within 30 days: WARNING
  - Guest account (informational): INFO
  - Non-compliant/stale device: WARNING
- Password generation: random, meets Entra default complexity, throwaway test account only
- License SKU: whatever's available in the dev tenant (document actual SKU used)
- Write confirmation mechanism: typed UPN required for --execute
- Rollback/reversibility per action:
  - disable sign-in: reversible
  - revoke refresh tokens: not reversible as an action, but practically non-permanent
  - remove from groups: reversible
  - reclaim license: reversible (subject to SKU pool availability)
  - mailbox → shared: not automated via Graph, documented as a known gap
- Certificate storage: Azure Key Vault
- Batching improvement metric: before/after Graph API call count for the same operation
- Permission widening rule: only widen a scope when a specific audit/write action requires it; document the scope and the action that required it at the time it's added
