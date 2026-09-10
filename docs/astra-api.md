# GPT-6 Astra: September 2026 API supplement

This supplement contains only direct OpenAI API measurements for `gpt-6-astra`.
It adds one neutral, Astra-only quadratic Student-t plot without changing the
four original datasets, their fit tables, or Figures 1–4. No subscription-route
observations, account-usage records, website source, or branded artwork are
included.

## Included observations and provenance

| Session | Measurement interval, UTC (September 9, 2026) | Planned blocks | Completed blocks | Measurements |
|---|---|---:|---:|---:|
| `20260909T123307Z-1c49feec` | 12:35:17–12:36:32 | 5 | 1 | 6 |
| `20260909T124315Z-c70b34b7` | 12:45:28–12:49:35 | 3 | 3 | 18 |

These intervals correspond to approximately 08:35–08:49 Eastern Daylight Time.
The first session was interrupted; its log has no `session_end`. An interrupted
in-flight request has no completed observation and is not represented as a
zero-latency result. The continuation has a complete end record. Two cache-setup
requests are retained in the raw logs for audit, but excluded from the fits and
plot. All 24 completed measurements belong to complete six-length blocks; none
were removed as latency outliers.

Each block contains one request at nominal totals of 50k, 150k, 250k, 300k, 550k,
and 900k input tokens. There are four measurements per length. The actual
provider-reported totals are respectively **49,998; 149,998; 249,998; 299,998;
549,998; and 899,998**. The figure and this supplement's regressions use those
actual totals, not nominal targets. The original four-model analysis remains
unchanged, including its historical fitting conventions.

Exact chronological order (lengths in thousands of tokens):

| Session / zero-based block | Request order |
|---|---|
| Initial / 0 | 250, 300, 900, 150, 550, 50 |
| Continuation / 0 | 250, 300, 150, 550, 900, 50 |
| Continuation / 1 | 50, 250, 900, 150, 550, 300 |
| Continuation / 2 | 300, 900, 250, 550, 150, 50 |

The corresponding `data/schedules/` CSVs retain full start/end timestamps and
use one-based block numbers. Logs retain zero-based repetitions. Regression
block IDs combine session ID and repetition so block 0 from the two sessions
is never treated as the same block.

## Collection protocol

The archived setting snapshot is [`config/astra_api.json`](../config/astra_api.json).
Requests were sequential, using the Responses endpoint `/v1/responses`,
`stream: true`, `store: false`, `service_tier: "default"`,
`reasoning: {"effort": "low"}`, and `max_output_tokens: 512`.
Temperature and top-p were omitted. Returned model and service tier match the
requested values for all 24 measurements.

Reasoning was **not disabled by an API parameter**: effort was `low`.
Nevertheless, all measured responses were `OK`, with five provider-reported
output tokens and **zero reported reasoning tokens**. The excluded setup
responses generated 10 and 12 reasoning tokens, respectively. Thus zero
reasoning is an observed property of the measured requests, not a capability
claim or a filter used to select particularly fast observations.

Prompts used the same pinned Gutenberg corpus already included in this repo
(SHA-256 `075768889cfef63bcbb967fa0204b6048201fdfe896124915f75e8dadc8b9e75`).
The two content blocks follow the existing [prompt construction](prompt-construction.md):

```text
content[0] = "REFERENCE TEXT:\n" + corpus[:split]
content[1] = "Benchmark nonce: " + sixteen space-separated digits + "\n"
             + corpus[split:end]
             + "\n\nTASK:\n"
             + "Do not think or analyze. Respond immediately with exactly one word: OK"
```

The nonce digits are `str(byte % 10)` for each byte in `uuid.uuid4().bytes`.
The corpus continuation is shared at a given length, but the nonce precedes it.
The prefix's explicit breakpoint is `prompt_cache_breakpoint: {"mode": "explicit"}`;
the request sets `prompt_cache_options: {"mode": "explicit"}` and a session-specific
`prompt_cache_key`. Each session first writes the prefix in a setup request and
validates the setup before measured requests begin. Each measured hit was then
checked against the expected cached-prefix count.

The requested prefix size was 2,048 tokens. Every measured response reports
**2,051 cache-read tokens and zero cache-write tokens**; all remaining input is
reported as new input. The stable prefix hash is identical across both sessions:
`730485e7e542bd012d1a7de896a57ef9d4048173bb8dcdc412e0127ef1738836`.
The sessions use distinct cache-key hashes, so this is not one continuously
reused cache identity across both runs. No claim of a fixed worker, accelerator,
or datacenter follows from the cache metadata.

Nominal target sizing included the prefix and used the provider's token-count
endpoint before timing. The final nonce/instruction construction differs from
the counting template; the observed totals are two tokens below nominal.
Logs retain prepared-prompt hashes, but not the exact nonce strings or final
serialized bodies. This supplement does not claim byte-identical replay of
historical requests.

The collector used one HTTP connection pool slot and a minimum four-second
interval between starts of request-loop iterations:

```python
time.sleep(max(0, 4.0 - (time.monotonic() - previous_start)))
previous_start = time.monotonic()
```

This is not a fixed four-second sleep after each response. Interactive checkpoints
between blocks could insert additional pauses. Local prompt construction,
serialization, and `client.build_request` preceded the monotonic TTFT start.
The timer started immediately before `client.send(request, stream=True)` and
ended at the first nonempty `response.output_text.delta`. It therefore includes
upload, transport/reconnection when needed, provider queueing/routing, prefill,
first visible token generation, and return transit. It does not isolate kernel
runtime or measure an architectural FLOP count.

## Offline reproduction and fit conventions

```bash
make astra
```

This uses only the released logs and R packages already required by the repo.
It does not load credentials, make API calls, use a private path, or load the
website's code or fonts. `make astra-figures` rerenders just the plot. The
existing public collector/config remains the historical four-model collector;
this supplement's JSON is an archived protocol specification, **not** a new
drop-in paid collection configuration.

[`analysis/astra_api.R`](../analysis/astra_api.R) fits:

```text
TTFT = alpha + beta*x [+ gamma*x^2] + block_offset + Student-t noise
x = provider-reported total input tokens / 1,000,000
```

Both forms use fixed degrees of freedom 4, a fitted positive scale sigma, and
four sum-to-zero block offsets (three free coefficients). Alpha, beta, and gamma
are unconstrained. Initialization uses `MASS::rlm` with Huber psi and 200 maximum
iterations, then residual MAD initializes sigma. BFGS uses `maxit=3000` and
`reltol=1e-11`, the settings used for the Astra figure analysis. Both optimizations
converge. The figure plots the quadratic baseline with block offset zero, while
retaining every raw measured request. Curves stop at the measured endpoints.

Both sessions are combined for the plotted fit. Block offsets absorb additive
shifts but not session-specific slope/curvature differences. Only four blocks
are available; pooling does not establish invariant latency across sessions.

| Fit | alpha (s) | beta (s/Mtoken) | gamma (s/Mtoken²) | sigma (s) | Log likelihood |
|---|---:|---:|---:|---:|---:|
| Student-t linear | -0.05316538408809164 | 31.24725659211617 | 0 | 0.8235928702934932 | -34.67113597247108 |
| Student-t quadratic | 1.481367987305519 | 20.47597298227532 | 11.63186186745642 | 0.4858116398000202 | -21.30692068001702 |

The stored likelihood-ratio statistic is 26.7284305849081; the asymptotic
chi-square(1) p-value is 2.34150869895418e-7. Linear minus quadratic AICc is
22.6696070554963. The chi-square reference is the usual nested-model approximation
with one additional unconstrained coefficient. This p-value assumes the fitted
independent-error model conditional on blocks; it is **not** a block-robust or
finite-sample calibrated significance claim. The small block count, possible
nonconstant variance, and uncertain noise mechanism warrant caution.

This scoped addition releases the plotted Student-t coefficients and their
linear comparator; it does not add Astra bootstrap CIs, asymmetric fits,
content experiments, or extrapolations. Do not reuse the original four models'
bootstrap intervals as Astra intervals.

## Files

- `data/raw/astra-api/`: sanitized original session records, including setup.
- `data/schedules/20260909*.csv`: exact observed order and wall-clock times.
- `outputs/astra-api/request_observations.csv`: 24 plotted observations.
- `outputs/astra-api/fit_coefficients.csv` and `student_fits.json`: both fits.
- `outputs/astra-api/fit_block_effects.csv`: all four offsets for each fit.
- `outputs/astra-api/linear_quadratic_comparison.csv`: LR and AICc comparison.
- `outputs/astra-api/quadratic_curve.csv`: the 300-point plotted baseline.
- `figures/astra-api/astra_api_student_t.{png,svg,pdf}`: neutral figure exports.

The neutral figure uses the repo's existing licensed Inter font and renderer.
It reproduces the API data and quadratic curve, not the branding or social/web
layout of the privately prepared report artwork.
