# Public-log redactions

The checked-in JSONL files preserve every field used by the analysis, including
wall-clock timestamps, monotonic timing components, token usage, request order,
cache accounting, model identifiers, validity flags, and estimated costs.

The release preparation script removes these operational fields:

- `hostname`
- `request_id`
- `response_id`
- `retry_after`
- `ratelimit_reset_tokens`
- `ratelimit_remaining_tokens`

They are not inputs to any reported calculation. Session IDs, hashed prompt and
cache identities, the general platform string, and the stated network location
are retained because they document the experimental setup without revealing API
credentials. API keys were loaded from `.env` and were never written to the logs.

The original private logs remain outside this repository.
