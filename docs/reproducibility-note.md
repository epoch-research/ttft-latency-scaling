# TTFT reproducibility note: regression and measurement details

This note records implementation details that are easy to omit from a methods
summary but matter for reproducing the finalized TTFT results. It is derived from
the selected JSONL logs and the analysis/collection code in this repository.
Statements that the artifacts do not establish are explicitly marked unresolved.

The four finalized sessions are:

| Model | Session ID | Requests | Blocks |
|---|---|---:|---:|
| GPT-5.6 Terra | `20260813T155415Z-6998d614` | 72 | 8 |
| GPT-5.6 Sol | `20260814T140715Z-bee825d8` | 30 | 5 |
| Claude Sonnet 5 | `20260814T154718Z-5dc271b9` | 112 | 14 |
| Claude Opus 5 | `20260813T163222Z-b3406d60` | 48 | 6 |

## 1. Block-effect sensitivity

These are quadratic Student-t maximum-likelihood fits with residual degrees of
freedom fixed at four. The input variable is:

```text
x = nominal target input tokens / 1,000,000
```

Thus, `gamma` has units of seconds per million-tokens squared. The block-adjusted
model is:

```text
TTFT = alpha + beta*x + gamma*x^2 + block_effect + Student-t(df=4, scale=sigma)
```

Its chronological-block effects use `contr.sum(K)`: `K-1` coefficients are
explicit and the final coefficient is their negative sum. The unadjusted
sensitivity fit uses the same likelihood, initialization, optimizer, and scaling
variables but omits the block columns.

Both versions initialize their location coefficients with a Huber `MASS::rlm`
fit, initialize scale as `max(mad(residual), 1e-3)`, parameterize scale as
`sigma = exp(log_sigma)`, and minimize negative Student-t log likelihood with
`optim(method="BFGS", maxit=2000, reltol=1e-10)`.

| Model | `gamma`, no block effects | `gamma`, with block effects | Relative change |
|---|---:|---:|---:|
| GPT-5.6 Terra | 7.772825426793649 | 8.026460965362830 | +3.26% |
| GPT-5.6 Sol | 10.468664645056569 | 10.415900440701023 | −0.50% |
| Claude Sonnet 5 | −0.193154253971251 | −0.205822643557970 | −6.56% relative to `abs(gamma_no_block)` |
| Claude Opus 5 | −0.217652499568692 | 1.575366868142133 | point estimate changes sign |

The block-adjusted values above are the authoritative Student-t coefficients in
[`outputs/tables/fit_coefficients.csv`](../outputs/tables/fit_coefficients.csv). The
no-block values were obtained by rerunning the same quadratic Student-t objective
with `x + I(x^2)` instead of `x + I(x^2) + block`.

For context, the corresponding linear-versus-quadratic likelihood-ratio p-values
were:

| Model | No block effects | With block effects |
|---|---:|---:|
| GPT-5.6 Terra | `1.84e-17` | `8.87e-19` |
| GPT-5.6 Sol | `9.36e-10` | `1.48e-10` |
| Claude Sonnet 5 | 0.748 | 0.711 |
| Claude Opus 5 | 0.960 | 0.701 |

Consequently, block adjustment is not responsible for the Terra/Sol curvature
finding or the Sonnet/Opus lack of significant curvature. Opus's noisy quadratic
point estimate is sensitive to the adjustment, but its statistical conclusion is
not.

The sum-to-zero constraint itself is only a parameterization choice. Replacing it
with reference-block treatment coding leaves fitted values, `beta`, `gamma`,
residuals, and likelihood unchanged; it changes the reported intercept and block
coefficients. Including versus omitting block effects is the substantive modeling
choice.

## 2. Exact 5,000-replicate Huber block bootstrap

The implementation is in
[`analysis/reproduce.R`](../analysis/reproduce.R), which contains the finalized
`huber_quadratic()` and `resample_blocks()` functions directly.

### Huber estimator

Every original and bootstrap Huber fit called:

```r
MASS::rlm(
  y ~ x + I(x^2) + block,
  data = data,
  psi = MASS::psi.huber,
  maxit = 200
)
```

The call did not override the remaining `rlm` defaults. In the analysis
environment currently present in the repository, MASS is version `7.3-60.0.1`,
and those defaults are:

```text
method    = "M"
init      = "ls"
scale.est = "MAD"
acc       = 1e-4
test.vec  = "resid"
Huber k   = 1.345
```

The initial coefficients therefore come from least squares. Iteratively reweighted
least squares uses standardized residual `u = residual/scale` and weight:

```text
w(u) = min(1, 1.345 / abs(u)).
```

Equivalently, apart from an additive/multiplicative convention, the Huber loss is:

```text
rho(u) = 0.5*u^2                              if abs(u) <= 1.345
         1.345*abs(u) - 0.5*(1.345^2)        otherwise.
```

With the default MAD scale option, each iteration uses:

```text
scale = median(abs(residual)) / 0.6745.
```

No observation weights were supplied. The quadratic coefficient was unconstrained:
`gamma` could be negative, zero, or positive.

The Huber bootstrap formula includes a quadratic term and a block factor. Unlike
the finalized likelihood fits, this particular `rlm` call does **not** explicitly
pass `contr.sum`; it uses R's default treatment coding for `block`. This does not
change `gamma` or the fitted values because both contrast systems span the same
block-effect nuisance space. It changes only the intercept/block-coefficient
representation.

### Whole-block resampling

For a dataset with `K` chronological blocks, one bootstrap replicate did:

```r
blocks <- levels(data$block)
selected <- sample(blocks, length(blocks), replace = TRUE)
```

Thus, exactly `K` original blocks were sampled with replacement. Every selected
block contributed all of its request rows, preserving the one-request-per-length
vector and within-block dependence.

Selections were relabeled by their draw position:

```r
piece$block <- paste0("boot_", new_block)
```

For example, if original block 3 was drawn twice, its two copies became distinct
pseudo-blocks such as `boot_2` and `boot_5`; they were not merged into one factor
level. The pieces were row-bound, the block column was converted to a fresh factor,
and row names were discarded.

The bootstrap used:

```r
set.seed(20260817)
bootstrap_count <- 5000
```

The seed was set once before iterating through the datasets in this order: Terra,
Sol, Sonnet, then Opus. Errors were converted to `NA`. All 5,000 replicates were
successful for every finalized dataset.

The reported 95% interval is the ordinary percentile interval:

```r
quantile(gamma_bootstrap, c(0.025, 0.5, 0.975), na.rm = TRUE)
```

Because no `type` argument was supplied, this uses R's default quantile algorithm,
`type = 7`. The reported fraction positive is:

```r
mean(gamma_bootstrap > 0, na.rm = TRUE)
```

The resulting fractions were 1.000 for Terra, 1.000 for Sol, 0.513 for Sonnet,
and 0.555 for Opus. The complete replicate-level output is
[`outputs/bootstrap/huber_block_bootstrap.csv`](../outputs/bootstrap/huber_block_bootstrap.csv).

### Software-version limitation

The repository does not contain a saved `sessionInfo()` from the original analysis
execution. `MASS 7.3-60.0.1` is the version in the current analysis environment and
is the version used for the verification above; the artifacts do not independently
prove the package version at every earlier exploratory execution.

## 3. Exact nonce construction

The measured-request nonce is constructed in
[`src/ttft_bench/cli.py`](../src/ttft_bench/cli.py) as:

```python
nonce = " ".join(str(byte % 10) for byte in uuid.uuid4().bytes)
suffix = f"Benchmark nonce: {nonce}\n{suffix}"
```

This procedure:

1. generates a fresh UUID version 4;
2. reads its 16 raw bytes in byte order;
3. maps each byte independently to one decimal digit using `byte % 10`;
4. converts each result to its decimal character;
5. joins the 16 digits with single ASCII spaces; and
6. prefixes the label and appends one newline.

It does not use the UUID integer, a hash of the UUID, or the decimal/hexadecimal
string representation of the UUID. An invented example is:

```text
Benchmark nonce: 4 7 0 2 9 1 6 6 3 8 2 5 0 9 4 1
```

The live nonce strings were not stored in the JSONL files, so their historical
values and absolute uniqueness cannot be audited afterward. The code establishes
fresh independent generation per call; collision probability is negligible but
not mathematically zero.

## 4. Exact clean-`sigma` anchor

The stochastic-frontier and spike-plus-contention fits do not estimate clean
Gaussian `sigma` jointly by maximum likelihood. They use a fixed anchor returned
by `estimate_clean_sigma()` in
[`analysis/reproduce.R`](../analysis/reproduce.R).

The pilot fit is:

```r
pilot <- MASS::rlm(
  y ~ x + I(x^2) + block,
  data = data,
  psi = MASS::psi.huber,
  maxit = 200,
  contrasts = list(block = contr.sum(nlevels(data$block)))
)
```

It is therefore a quadratic Huber M-estimator with the same default `k = 1.345`
and MAD-scale IRLS procedure described above. It includes sum-coded chronological
block effects. From its raw residuals `r = y - fitted`, the anchor is:

```r
lower_side <- r[r <= 0]
sigma_anchor <- max(
  0.02,
  median(abs(lower_side)) / qnorm(0.75)
)
```

Here `qnorm(0.75) = 0.6744897501960817`; the floor is 0.02 seconds. The finalized
anchors were:

| Model | Fixed clean `sigma` (seconds) |
|---|---:|
| GPT-5.6 Terra | 0.229863139297879 |
| GPT-5.6 Sol | 0.330218286132028 |
| Claude Sonnet 5 | 0.277712398629350 |
| Claude Opus 5 | 1.283576660793360 |

The same anchor for a model is used by its original frontier and spike fits. In
every asymmetric whole-block bootstrap replicate, the pilot is rerun on the
resampled blocks and `sigma_anchor` is recomputed before either asymmetric model
is fitted. It is not carried unchanged from the original dataset into the
bootstrap replicate.

## 5. Exact input-token and cache accounting

The statements “OpenAI actual input was nominal minus two” and “Anthropic actual
input was nominal minus six” hold for **every valid measured request in all four
finalized sessions**.

### OpenAI

| Model applicability | Nominal target | Provider-reported total | Cache read | Cache write | New input |
|---|---:|---:|---:|---:|---:|
| Terra, Sol | 50,000 | 49,998 | 2,051 | 0 | 47,947 |
| Terra only | 100,000 | 99,998 | 2,051 | 0 | 97,947 |
| Terra, Sol | 175,000 | 174,998 | 2,051 | 0 | 172,947 |
| Terra, Sol | 250,000 | 249,998 | 2,051 | 0 | 247,947 |
| Terra, Sol | 275,000 | 274,998 | 2,051 | 0 | 272,947 |
| Terra only | 375,000 | 374,998 | 2,051 | 0 | 372,947 |
| Terra, Sol | 550,000 | 549,998 | 2,051 | 0 | 547,947 |
| Terra only | 750,000 | 749,998 | 2,051 | 0 | 747,947 |
| Terra, Sol | 850,000 | 849,998 | 2,051 | 0 | 847,947 |

This invariant holds across all 72 Terra and 30 Sol measurements.

### Anthropic

| Model applicability | Nominal target | Provider-reported total | Cache read | Cache write | New input |
|---|---:|---:|---:|---:|---:|
| Sonnet, Opus | 50,000 | 49,994 | 2,052 | 0 | 47,942 |
| Sonnet, Opus | 100,000 | 99,994 | 2,052 | 0 | 97,942 |
| Sonnet, Opus | 175,000 | 174,994 | 2,052 | 0 | 172,942 |
| Sonnet, Opus | 250,000 | 249,994 | 2,052 | 0 | 247,942 |
| Sonnet, Opus | 375,000 | 374,994 | 2,052 | 0 | 372,942 |
| Sonnet, Opus | 550,000 | 549,994 | 2,052 | 0 | 547,942 |
| Sonnet, Opus | 750,000 | 749,994 | 2,052 | 0 | 747,942 |
| Sonnet, Opus | 900,000 | 899,994 | 2,052 | 0 | 897,942 |

This invariant holds across all 112 Sonnet and 48 Opus measurements. In every row,
`new input + cache read + cache write = total input` exactly.

## 6. Pacing implementation

Every finalized session header records:

```text
shared_cache_min_interval_seconds = 4.0
```

The current shared-prefix loop implements:

```python
previous_start = time.monotonic()
for request in schedule:
    time.sleep(max(
        0,
        4.0 - (time.monotonic() - previous_start),
    ))
    previous_start = time.monotonic()
    run_request()
```

This targets four seconds between monotonic **dispatch markers** immediately
before calls into the request-writing function. It is not a four-second delay
after completion. When the preceding call already took at least four seconds, no
sleep is inserted.

It is also not exactly four seconds between the JSONL `request_started_at` wall
timestamps. Prompt reconstruction, JSON serialization, and HTTP request-object
creation happen inside `run_request()` after the dispatch marker but before the
recorded request start. The dispatch markers were not persisted. In addition,
wall-clock timestamps can adjust independently of the monotonic clock used for
TTFT and pacing.

The observed consecutive measured-request wall-clock start intervals were:

| Session | Number of intervals | Median | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Terra | 71 | 4.013816118 s | 2.145069838 s | 16.203249931 s |
| Sol | 29 | 4.749557018 s | 3.852861881 s | 19.131859064 s |
| Sonnet | 111 | 4.387102127 s | 3.997616053 s | 17.290031195 s |
| Opus | 47 | 9.001471043 s | 4.001052141 s | 25.440265894 s |

These are descriptive wall-clock intervals, not direct observations of the
unlogged monotonic dispatch-marker intervals.

## 7. Timing boundary and HTTP connection behavior

For each request, the code first:

1. constructs the provider payload and text blocks;
2. serializes the complete payload to compact UTF-8 JSON bytes; and
3. calls `client.build_request(...)` to create the HTTP request object.

Only then does it record:

```python
request_started_at = datetime.now(timezone.utc).isoformat()
started = time.perf_counter_ns()
```

The timer starts at
[`src/ttft_bench/cli.py`](../src/ttft_bench/cli.py), immediately after request-object
construction and before creation of the result-record dictionary and
`client.send(request, stream=True)`. Therefore, TTFT excludes corpus slicing,
payload construction, JSON serialization, and `build_request`, but includes the
small amount of local bookkeeping between `started` and `client.send`.

The stopping point is the first nonempty text delta:

- OpenAI: first nonempty `response.output_text.delta`;
- Anthropic: first `content_block_delta` with `delta.type == "text_delta"` and
  nonempty text.

The elapsed time is measured throughout with `time.perf_counter_ns()`. It includes
request-body transmission, public-network time, provider routing/queueing/cache
lookup/prefill, and return through the first text delta.

One synchronous `httpx.Client` was used per model with:

```python
httpx.Limits(max_connections=1, max_keepalive_connections=1)
```

Prior token-count calls used the same client and normally established a reusable
connection. If HTTPX had to reconnect because no reusable connection was
available, DNS lookup, TCP connection, and TLS setup occurring inside
`client.send` would be included in TTFT. The benchmark did not log connection-pool
events, DNS, TCP, TLS, HTTP version, or reconnect status, so whether an individual
measurement reconnected is unresolved.

## 8. Exact A.5 MAD calculation

The reported MAD is the **unscaled** median absolute deviation:

```text
MAD(y) = median(abs(y - median(y))).
```

It is not R's default consistency-scaled `stats::mad()` value.

The uncached comparison combines two Sonnet sessions:

- `20260812T191605Z-bae8e752`: one request per length;
- `20260812T192643Z-50c12a81`: four requests per length.

The shared-prefix comparison uses finalized Sonnet session
`20260814T154718Z-5dc271b9`, with 14 requests per length. These sessions were run
on different dates and are an observational comparison, not a randomized
before/after experiment. They also differ in prompt/output procedure: the early
uncached sessions used the summarization prompt, whereas the finalized shared-prefix
session used the fixed one-word `OK` instruction and leading nonce.

### 100k input tokens

Uncached, `n = 5`, sorted TTFT values in seconds:

```text
2.559515110, 2.729865546, 2.877659149, 3.327111885, 7.478986140
```

```text
median = 2.877659149
sorted absolute deviations =
0, 0.147793603, 0.318144039, 0.449452736, 4.601326991
MAD = 0.318144039 seconds
```

Shared prefix, `n = 14`, sorted TTFT values in seconds:

```text
1.508718313, 1.576265737, 1.591200718, 1.625554483,
1.664270800, 1.697843513, 1.723689655, 1.723865010,
1.762443844, 1.862722521, 1.945508103, 1.988969166,
2.142223860, 2.234296517
```

```text
median = (1.723689655 + 1.723865010) / 2 = 1.7237773325
middle absolute deviations = 0.1325766145, 0.1389451885
MAD = (0.1325766145 + 0.1389451885) / 2
    = 0.1357609015 seconds
```

This is the reported rounded change `0.318 -> 0.136` seconds.

### 250k input tokens

Uncached, `n = 5`, sorted TTFT values in seconds:

```text
3.606167333, 4.817498313, 5.169160448, 5.389365029, 11.530882175
```

```text
median = 5.169160448
sorted absolute deviations =
0, 0.220204581, 0.351662135, 1.562993115, 6.361721727
MAD = 0.351662135 seconds
```

Shared prefix, `n = 14`, sorted TTFT values in seconds:

```text
3.400184775, 3.420393061, 3.455448937, 3.460223273,
3.483004241, 3.541679406, 3.552240217, 3.576902337,
3.614667014, 3.629604452, 3.681282207, 3.834073560,
3.873150860, 3.989710407
```

```text
median = (3.552240217 + 3.576902337) / 2 = 3.564571277
middle absolute deviations = 0.104348004, 0.109122340
MAD = (0.104348004 + 0.109122340) / 2
    = 0.106735172 seconds
```

This is the reported rounded change `0.352 -> 0.107` seconds.

## Facts versus interpretation

Directly established by code and logs:

- exact Student-t `gamma` values above;
- exact Huber call, block-resampling algorithm, seed, percentile calculation,
  and successful replicate counts;
- exact UUID-byte-to-digit nonce transformation;
- exact Huber pilot and clean-`sigma` formula;
- exact provider-reported token/cache accounting;
- configured pacing value and recorded wall-clock intervals;
- timer placement and first-text-delta stopping rule; and
- exact samples and arithmetic used for the MAD comparison.

Not directly observed:

- provider hardware, queueing, batching, routing, or cache placement;
- whether an individual HTTP request reused or re-established its connection;
- monotonic dispatch-marker timestamps for the historical sessions;
- historical nonce values; and
- a saved original R `sessionInfo()` proving package versions independently of
  the current environment.
