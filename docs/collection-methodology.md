# TTFT benchmark data-collection methodology

This document records the data-collection procedure for the four sessions used in
the finalized four-model TTFT figures. It is based on the JSONL session logs, the
benchmark implementation in `src/ttft_bench/cli.py`, `config/benchmark.toml`, the
pinned corpus manifest, and the experiment notes in
`docs/statistical-methodology.md`. Statements that cannot be recovered
from those artifacts are marked unresolved rather than inferred.

For a byte- and block-level account of the prompts, including the exact cached
prefix boundaries, target-specific corpus offsets, nonce construction, and the
difference between sizing and measured prompts, see
[`prompt-construction.md`](prompt-construction.md).

For exact regression sensitivity, bootstrap, clean-noise-anchor, token-accounting,
pacing, timing-boundary, and MAD-reproduction details, see
[`reproducibility-note.md`](reproducibility-note.md).

The finalized analysis uses one session per model. In particular, it does **not**
pool Claude sessions from different dates.

## 1. Finalized sessions

All four sessions used the `shared_prefix_cached` mode. Each completed successfully,
and every measured row in each file is marked valid. The Sol and Sonnet session-end
records additionally report zero failed attempts and zero missing measurements. The
older Terra and Opus session-end records do not contain those counters, although
their files contain no invalid sample rows.

Times below are America/Toronto local time (EDT, UTC-04:00). “Measured span” runs
from the start of the first measured request to completion of the last measured
request; it excludes prompt sizing, the token-count connection warm-up, and the
cache-setup request.

| Display name | Exact session ID | Session label | API model identifier | Date and measured span | Requests | Blocks | Nominal context lengths | Repetitions per length |
|---|---|---|---|---|---:|---:|---|---:|
| GPT-5.6 Terra | `20260813T155415Z-6998d614` | `terra-shared-prefix-scaling-large` | `gpt-5.6-terra` | 2026-08-13, 11:58:02–12:05:00 EDT | 72 | 8 | 50k, 100k, 175k, 250k, 275k, 375k, 550k, 750k, 850k | 8 |
| GPT-5.6 Sol | `20260814T140715Z-bee825d8` | `sol-morning-shared-prefix-repeat` | `gpt-5.6-sol` | 2026-08-14, 10:09:36–10:13:32 EDT | 30 | 5 | 50k, 175k, 250k, 275k, 550k, 850k | 5 |
| Claude Sonnet 5 | `20260814T154718Z-5dc271b9` | `sonnet-shared-prefix-more-blocks` | `claude-sonnet-5` | 2026-08-14, 11:48:41–12:00:54 EDT | 112 | 14 | 50k, 100k, 175k, 250k, 375k, 550k, 750k, 900k | 14 |
| Claude Opus 5 | `20260813T163222Z-b3406d60` | `opus-shared-prefix-scaling-large` | `claude-opus-5` | 2026-08-13, 12:33:47–12:42:12 EDT | 48 | 6 | 50k, 100k, 175k, 250k, 375k, 550k, 750k, 900k | 6 |

“Requests” in this table means fitted, measured generation requests. Each session
also made one excluded cache-setup generation and multiple token-count API calls
during prompt sizing. The exact number of token-count calls was not logged.

The session header was written somewhat earlier than the measured span because
prompt construction and provider token counting occurred before cache setup. Header
times were 11:54:15 EDT for Terra, 10:07:15 for Sol, 11:47:18 for Sonnet, and
12:32:22 for Opus. All four session headers record `network_label=home-toronto`.
The public APIs do not reveal the server region or datacenter.

### Request execution and HTTP connection

Requests were sequential, not concurrent. The implementation uses one synchronous
`httpx.Client` per model with both `max_connections=1` and
`max_keepalive_connections=1`. The next request is not issued until the preceding
stream is consumed and closed. The request-start/completion timestamps also show no
overlap. Consequently, the benchmark measures one in-flight generation at a time
over a reused client connection.

The exact command-line invocations were not persisted, but the resulting session
headers preserve the effective model, lengths, repetition count, cache mode,
shared-prefix target, output mode, nonce mode, and spacing configuration.

### Generation and streaming parameters

The common output limit was 32 tokens (`max_output_tokens=32` for OpenAI and
`max_tokens=32` for Anthropic). Every measured request used streaming.

OpenAI requests were sent to `POST /v1/responses` with:

```json
{
  "reasoning": {"effort": "none"},
  "service_tier": "default",
  "stream": true,
  "store": false,
  "max_output_tokens": 32
}
```

Anthropic requests were sent to `POST /v1/messages` with:

```json
{
  "thinking": {"type": "disabled"},
  "stream": true,
  "max_tokens": 32
}
```

No temperature, `top_p`, sampling seed, tools, or stop sequences were supplied for
these sessions; provider defaults therefore applied for any omitted parameter.
Neither Sonnet nor Opus had an Anthropic `output_config.effort` setting. The prompt
ended with:

> Do not think or analyze. Respond immediately with exactly one word: OK

All finalized OpenAI responses reported five output tokens and zero reasoning
tokens. All finalized Anthropic responses reported four output tokens and zero
thinking blocks. Every measured output passed the benchmark's exact `OK` compliance
check. These checks keep hidden reasoning or a long answer from becoming a TTFT
confound; TTFT itself ends at the first text delta and does not depend on how many
tokens arrive afterward.

### TTFT timestamp and calculation

The request payload is constructed and compact-JSON serialized before the timer
starts. The client request object is also built before timing. Immediately before
`client.send(request, stream=True)`, the benchmark records both a UTC wall-clock
timestamp and `time.perf_counter_ns()`.

It then parses the server-sent-event stream. TTFT is:

```text
TTFT = monotonic time of first non-empty text delta
       - monotonic time immediately before client.send(...)
```

For OpenAI, the stopping event is the first nonempty
`response.output_text.delta`. For Anthropic, it is the first
`content_block_delta` whose delta type is `text_delta` and whose text is nonempty.
HTTP-header arrival, first SSE event, and content-block creation are recorded
separately and are not substituted for TTFT.

This definition excludes local prompt assembly, token counting, JSON serialization,
and request-object construction. It includes request-body upload, public-network
latency, provider routing and queueing, prompt-cache lookup, prefill/serving work,
and the return path through the first text delta. The provider APIs do not expose
those components separately.

### Exact chronological ordering

Within each block, one request was made at every context length. The list was
pseudorandomly shuffled rather than sorted. Blocks themselves remained in
chronological repetition order. The session-specific random generator was seeded
from the configured seed `20260812` XORed with the final eight hexadecimal
characters of the generated session ID.

The exact nominal-token order recovered from each JSONL file is:

**GPT-5.6 Terra**

```text
B1: 850k, 750k, 375k, 50k, 550k, 175k, 275k, 250k, 100k
B2: 550k, 50k, 250k, 750k, 100k, 375k, 850k, 175k, 275k
B3: 250k, 550k, 850k, 100k, 375k, 50k, 175k, 275k, 750k
B4: 175k, 250k, 550k, 275k, 375k, 50k, 750k, 100k, 850k
B5: 275k, 175k, 550k, 50k, 850k, 250k, 750k, 375k, 100k
B6: 375k, 750k, 50k, 250k, 550k, 175k, 100k, 275k, 850k
B7: 375k, 100k, 750k, 275k, 550k, 50k, 250k, 850k, 175k
B8: 250k, 750k, 275k, 175k, 100k, 550k, 50k, 850k, 375k
```

**GPT-5.6 Sol**

```text
B1: 250k, 175k, 850k, 275k, 50k, 550k
B2: 275k, 550k, 175k, 250k, 50k, 850k
B3: 850k, 550k, 275k, 50k, 250k, 175k
B4: 250k, 275k, 550k, 175k, 850k, 50k
B5: 850k, 250k, 175k, 50k, 275k, 550k
```

**Claude Sonnet 5**

```text
B1:  50k, 550k, 250k, 375k, 175k, 750k, 900k, 100k
B2:  50k, 175k, 375k, 550k, 100k, 900k, 750k, 250k
B3:  250k, 100k, 900k, 750k, 175k, 50k, 375k, 550k
B4:  250k, 175k, 375k, 550k, 100k, 50k, 750k, 900k
B5:  250k, 550k, 375k, 50k, 900k, 100k, 750k, 175k
B6:  900k, 250k, 100k, 375k, 750k, 550k, 175k, 50k
B7:  250k, 750k, 375k, 100k, 550k, 900k, 175k, 50k
B8:  375k, 175k, 900k, 50k, 250k, 550k, 750k, 100k
B9:  375k, 100k, 175k, 550k, 250k, 900k, 750k, 50k
B10: 250k, 375k, 175k, 900k, 750k, 50k, 550k, 100k
B11: 250k, 100k, 50k, 550k, 375k, 900k, 175k, 750k
B12: 750k, 900k, 375k, 175k, 50k, 100k, 550k, 250k
B13: 750k, 900k, 100k, 175k, 250k, 375k, 550k, 50k
B14: 750k, 175k, 250k, 900k, 375k, 50k, 100k, 550k
```

**Claude Opus 5**

```text
B1: 550k, 175k, 375k, 50k, 100k, 750k, 900k, 250k
B2: 50k, 550k, 175k, 750k, 900k, 250k, 375k, 100k
B3: 550k, 50k, 750k, 175k, 100k, 900k, 375k, 250k
B4: 100k, 375k, 900k, 750k, 175k, 550k, 50k, 250k
B5: 50k, 375k, 900k, 175k, 750k, 100k, 550k, 250k
B6: 50k, 375k, 550k, 750k, 900k, 100k, 175k, 250k
```

### Inter-request spacing

Each session header records `shared_cache_min_interval_seconds=4.0`. The current
implementation sleeps, when needed, to target at least four seconds between request
starts; this setting was motivated by OpenAI's documented recommendation to keep a
single prompt-cache key at roughly 15 requests per minute or below.

The raw timestamps are the authoritative record of what actually happened. Their
request-start intervals were:

| Session | Median start interval | Minimum | Maximum | Intervals below 3.99 s |
|---|---:|---:|---:|---:|
| Terra | 4.014 s | 2.145 s | 16.203 s | 6 |
| Sol | 4.750 s | 3.853 s | 19.132 s | 1 |
| Sonnet | 4.387 s | 3.998 s | 17.290 s | 0 |
| Opus | 9.001 s | 4.001 s | 25.440 s | 0 |

Thus, it is safe to report a configured four-second pacing target, but not that
every historical request start was at least four seconds apart. One of Terra's six
sub-four-second intervals crosses a block boundary; the other five are within
blocks. The repository does not carry version-control metadata or a stored source
revision for the executed sessions, so the discrepancy between those timestamps
and the current loop implementation cannot be resolved more specifically. There
were no configured long cool-downs between blocks. Longer gaps can arise naturally
when the prior streaming request itself takes longer than four seconds; the logs do
not identify any additional cause separately.

## 2. Shared-prefix construction

### Corpus and prompt structure

The source corpus was a pinned concatenation of seven Project Gutenberg texts in
manifest order, with a document heading inserted before each text:

1. *Pride and Prejudice*;
2. *Moby-Dick*;
3. *Frankenstein*;
4. *The Adventures of Sherlock Holmes*;
5. *Alice's Adventures in Wonderland*;
6. *A Tale of Two Cities*;
7. *War and Peace*.

Downloaded bytes were checked against the SHA-256 values in
`data/corpus/manifest.json`; line endings were normalized, and the combined corpus hash
recorded in every final session was
`075768889cfef63bcbb967fa0204b6048201fdfe896124915f75e8dadc8b9e75`.

For a cached prompt, the logical request content was:

```text
[cached stable block]
REFERENCE TEXT:
{corpus from character 0 through split point}

[uncached continuation block]
Benchmark nonce: {16 one-digit values separated by spaces}
{corpus from split point through target-specific end point}

TASK:
Do not think or analyze. Respond immediately with exactly one word: OK
```

The 16 nonce digits were derived from a fresh UUID's 16 bytes modulo 10. The nonce
was placed at the start of the uncached continuation so every measured continuation
was unique while leaving the cached prefix byte-for-byte unchanged. Apart from this
nonce, longer prompts were nested extensions of the same corpus rather than
independently sampled texts.

### Selecting the split and target length

The requested shared-prefix size was 2,048 provider tokens. For each provider/model,
the code used the provider's token-count endpoint and binary-searched the shortest
prompt's character range for the first split whose stable part accounted for at
least 2,048 tokens. It then asserted that both the stable bytes and provider-token
count were unchanged at every target length. The realized cached prefix was:

| Provider sessions | Requested | Realized cache read on every measured request | Stable-prefix SHA-256 |
|---|---:|---:|---|
| Terra and Sol | 2,048 | 2,051 OpenAI tokens | `730485e7e542bd012d1a7de896a57ef9d4048173bb8dcdc412e0127ef1738836` |
| Sonnet and Opus | 2,048 | 2,052 Anthropic tokens | `ce8dc4f87e97c83ecc044c11b36a37bc895d11af4f881ee5ac55919cf192a477` |

The prefix was identical across all requests within a session. It was also
byte-identical between the two OpenAI sessions and between the two Anthropic
sessions, as established by the stable-prefix hashes. It was not byte-identical
across providers: provider tokenization led the binary search to a different
character split, and the logged hashes differ. The OpenAI cache key itself was
session-specific, of the form `ttft:shared:{session_id}:{model_id}`; Anthropic had
no equivalent application-supplied cache-key field.

For each nominal target, the code binary-searched the corpus end character and kept
the largest prompt whose provider token count did not exceed the requested total.
The nominal target includes the cached prefix. This is a small cached prefix plus a
large new continuation, not a benchmark in which most of the measured context was
already cached. The measured new-input ranges were 47,947–847,947 tokens for the
OpenAI sessions and 47,942–897,942 for the Anthropic sessions.

Actual total input was consistently two tokens below nominal for OpenAI (for
example, 849,998 at the 850k target) and six tokens below nominal for Anthropic
(899,994 at the 900k target). Two verified implementation details explain why an
exact nominal match was not guaranteed:

- binary search chose the largest character cutoff with a counted total less than
  or equal to the target, rather than adding padding to force equality;
- prompt sizing used the configured summarization instruction and a fixed all-zero
  nonce, while the final request substituted the fixed-`OK` instruction and a
  fresh UUID-derived nonce, which tokenized slightly differently.

The provider-returned `total_input_tokens`, rather than the nominal target, is used
as the regression x-variable in the finalized analysis.

### Provider-specific cache controls and observable hits

OpenAI placed `prompt_cache_breakpoint: {"mode":"explicit"}` on the stable input
block, sent `prompt_cache_options: {"mode":"explicit"}`, and reused the same
session-specific `prompt_cache_key` for all cache setup and measured requests.
OpenAI's official documentation says cache matching requires an exact prefix and
describes routing based primarily on `prompt_cache_key`, with the prefix hash as a
secondary input. It also exposes `cached_tokens` and `cache_write_tokens` in usage
metadata. See the [OpenAI prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching).

Anthropic placed `cache_control: {"type":"ephemeral","ttl":"5m"}` on the stable
text block and used the `anthropic-version: 2023-06-01` header. Its documentation
describes an exact reusable prefix through the explicit breakpoint, a five-minute
TTL refreshed on use, and the `cache_read_input_tokens` and
`cache_creation_input_tokens` usage fields. See the [Anthropic prompt-caching
guide](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
No Anthropic beta header was set by the benchmark.

Cache hits were therefore directly observable, not inferred from latency. The
setup request reported zero cache reads and a write of exactly 2,051 tokens for
OpenAI or 2,052 for Anthropic. Every finalized measured response reported a read of
that exact amount and zero cache-write tokens. The benchmark also checked that:

- cache read was at least the requested 2,048 tokens and matched the setup count;
- cache writes were zero;
- reported new + cache-read + cache-write tokens equaled total input tokens;
- total input stayed within the code's 64-token validation tolerance; and
- a first text delta existed with reasoning/thinking disabled.

A failure of these checks would abort the shared-prefix session rather than silently
reclassify the request.

### Cache setup and excluded requests

The session first called the provider token-count endpoint with a tiny “connection
warmup” input. This established DNS/TCP/TLS state without adding a paid generation
observation. Because `skip_warmup=true`, there was no separate inference sample
labeled `connection_warmup`.

Next, one excluded `cache_setup` generation wrote the stable prefix. It was not a
zero-output call; it used the same 32-token output ceiling and produced an ordinary
response, but it was labeled `kind=cache_setup` and excluded from all fits. Cache
setup began at 11:57:56 EDT for Terra, 10:09:31 for Sol, 11:48:35 for Sonnet, and
12:33:42 for Opus. The first measured request began about four seconds after setup
completed in every session. There was no polling loop that waited for an
out-of-band cache state. Instead, the setup response had to report the expected
write, and the first and every subsequent measured request had to report the
expected read.

No measured “first hit” was discarded. Once setup succeeded, all cache-hit
requests—including the first—were retained.

## 3. Empirical motivation for the shared prefix

The experiment notes describe a working serving-time model in which the observed
TTFT is a relatively stable context-dependent component plus nonnegative or mostly
positive delay from contention, routing, batching, or queueing. Early requests
without an explicit shared cache identity sometimes formed a low-latency cluster
plus much slower observations at the same context length. The shared-prefix design
was introduced as a practical attempt to hold the routing/cache cohort more nearly
constant while leaving almost all of the context new and therefore still measuring
prefill scaling.

“Without a shared prefix” should not be read as different natural-language data for
every request: those pilots used the same underlying nested corpus construction.
They were cache misses with no reusable 2k cached prefix/cache identity.

### Robust before/after dispersion checks

The following checks were recomputed directly from the pilot JSONL files. For each
context length, `MAD` is the unscaled median absolute deviation from that length's
median, and `IQR` is Q75−Q25 using linear interpolation. “Median cell” takes the
median of those statistics across matched context lengths. “Pooled residual” first
subtracts each context length's median and then computes dispersion across the
centered residuals.

These are observational before/after comparisons, not randomized controlled
experiments. Sessions occurred at different times, sometimes on different dates;
sample counts differ; and the early Opus cache-miss baseline had only two requests
per length.

| Comparison over matched lengths | Requests | Median cell MAD | Median cell IQR | Pooled residual MAD | Pooled residual IQR |
|---|---:|---:|---:|---:|---:|
| Sonnet uncached pilots, 100k/250k/750k | 15 | 0.318 s | 0.597 s | 0.318 s | 0.587 s |
| Sonnet finalized shared prefix, same lengths | 42 | 0.136 s | 0.290 s | 0.156 s | 0.398 s |
| Opus uncached pilot, 50k/250k/375k/750k | 8 | 0.410 s | 0.410 s | 0.410 s | 0.797 s |
| Opus 5-block shared-prefix pilot, same lengths | 20 | 0.157 s | 0.210 s | 0.169 s | 0.344 s |
| Terra uncached pilots, 50k/250k/375k/750k | 20 | 0.314 s | 0.795 s | 0.347 s | 0.964 s |
| Terra 5-block shared-prefix pilot, same lengths | 20 | 0.366 s | 0.505 s | 0.302 s | 0.608 s |
| Sol finalized uncached, six matched lengths | 36 | 0.197 s | 0.546 s | 0.196 s | 0.623 s |
| Sol finalized shared prefix, same lengths | 30 | 0.220 s | 0.312 s | 0.166 s | 0.297 s |

The early Sonnet cache-miss measurements illustrate the motivating problem. At
100k, five observations ranged from 2.560 to 7.479 seconds; at 250k, from 3.606 to
11.531 seconds; and at 500k, from 6.496 to 13.292 seconds with a 4.062-second IQR.
At the matched 100k and 250k lengths, the final shared-prefix Sonnet session reduced
MAD from 0.318 to 0.136 seconds and 0.352 to 0.107 seconds, respectively. At 750k,
however, MAD increased from 0.284 to 0.356 seconds. The effect was not uniform by
length.

The small Opus pilot also looked cleaner in aggregate after adding the shared
prefix: median-cell MAD fell about 62% and pooled-residual IQR about 57%. That
comparison is weak because its uncached baseline had only two samples per length,
and the 250k shared-prefix cell was substantially noisier than its uncached
counterpart. More importantly, the finalized 48-request Opus shared-prefix session
was itself noisy: its median-cell MAD was 0.954 seconds and median-cell IQR was
2.255 seconds. A shared prefix therefore did not guarantee a low-dispersion Opus
run.

OpenAI results were mixed rather than null. In the matched Terra pilots,
median-cell MAD was 17% higher with a shared prefix, while median-cell IQR and
pooled-residual IQR were about 37% lower. For Sol, median-cell MAD was 12% higher,
while median-cell IQR was 43% lower and pooled-residual IQR was 52% lower. Which
method looks “cleaner” depends on the dispersion summary.

The evidence does **not** establish that the variance reduction was generally
larger for Claude than for GPT. It establishes that large same-length dispersion in
early Claude cache-miss pilots motivated the design, that some subsequent
shared-prefix pilots were visibly cleaner, and that the effect was neither
universal nor controlled. The method was retained because it creates a validated,
reproducible cache cohort while keeping almost all tokens new—not because the
available data prove a provider-wide variance-reduction effect.

### Runs superseded or excluded from the finalized comparison

- Early Luna, GPT-5.5, Fable, sparse Sonnet/Opus, and routing pilots were used to
  refine the procedure but are not among the four finalized sessions.
- Large-cached-prefix experiments with only roughly 1k–10k new suffix tokens were
  excluded from scaling inference because the new-prefill signal was too small
  relative to latency noise. They answer a different cached-hit question.
- Incomplete shared-prefix pilots and their resumed fragments were not substituted
  for a complete final session.
- The valid Sol uncached session `20260813T174810Z-877203e7` remains a useful
  sensitivity dataset, but the four-model headline comparison uses the later
  shared-prefix Sol session to keep collection mode consistent.
- Separate-day Sonnet and Opus sessions were not pooled in the final plots after
  analysis showed session-level differences. The selected Sonnet session is the
  2026-08-14 14-block run; the selected Opus session is the 2026-08-13 6-block run.

The main comparison artifacts behind those decisions were Sonnet cache-miss
sessions `20260812T191605Z-bae8e752` and `20260812T192643Z-50c12a81`, the incomplete
and resumed 1,024-token Sonnet affinity pilots `20260812T210421Z-0d4debe7` and
`20260812T210627Z-7267b03c`, Opus cache-miss pilot
`20260813T142834Z-638a096e`, Opus five-block affinity pilot
`20260813T143911Z-b976fc5b`, the separate six-block Sonnet session
`20260813T165440Z-0e5adc75`, and the separate morning Opus session
`20260814T134405Z-c4566a73`. Exclusion was done at the session/design level; high
TTFT points were not deleted from the selected session plots or fits merely because
they appeared noisy.

## 4. Cache-affinity interpretation

Three levels of claim must remain separate.

### What the API behavior establishes

The logs establish that every measured request reused the exact same short prefix
within its session, that the provider counted that prefix as a cache read, and that
the large continuation was counted as new input. For OpenAI, one stable
`prompt_cache_key` was also reused within the session. OpenAI's public documentation
explicitly says that prompt-cache routing uses `prompt_cache_key` and prefix hash to
select a machine before a local cache lookup. Anthropic's public documentation
establishes exact-prefix caching and observable cache reads but does not document an
equivalent application-visible routing key or promise a particular worker.

### What the latency behavior suggests

Where shared-prefix runs show less same-length dispersion, it is consistent with
requests being handled by a narrower or more stable cache/routing cohort than
cache-miss requests. That is an interpretation of an observational latency change,
not a direct measurement of worker identity. The mixed Terra/Sol results and noisy
final Opus run show that cache affinity, even if present, does not remove load,
scheduling, networking, or within-cohort variability.

### What remains architectural speculation

The artifacts do not establish that requests land on the same accelerator, GPU
node, CPU host, datacenter, hardware generation, or serving configuration. They do
not locate cached KV state in CPU DRAM, accelerator HBM, local disk, or a remote
cache service. Even OpenAI's documentation-level use of “machine” does not reveal
accelerator identity or prove that every request with the same key uses one physical
host throughout a session. Claims at that level should remain hypotheses.

## 5. Anthropic versus OpenAI noise

The strongest evidence for unusually large noise in unrelated/non-affinity Claude
requests comes from the early Sonnet cache-miss cells cited above: individual
same-length observations differed by 4.9–7.9 seconds at 100k–500k. The early Opus
cache-miss pilot was smaller and less dramatic, although its 375k pair differed by
2.00 seconds. Some shared-prefix Claude pilots tightened substantially, especially
the 100k and 250k Sonnet cells and three of four Opus pilot cells.

That pattern should not be paraphrased as “Anthropic uses heterogeneous hardware.”
The APIs did not expose hardware, routing decisions, cache location, scheduler
state, datacenter, or concurrent load. Plausible sources of request-dependent
variation include different serving configurations, transient load, datacenter or
network path, cache placement, scheduler and batching state, or different hardware
generations. None was measured independently here. Heterogeneous hardware is one
possible explanation among several, not an experimental result.

Nor do the finalized sessions support a simple claim that Claude is always noisier
than OpenAI. Robust dispersion for the four selected sessions was:

| Finalized session | Median cell MAD | Median cell IQR | Pooled residual MAD | Pooled residual IQR |
|---|---:|---:|---:|---:|
| Terra shared prefix | 0.156 s | 0.362 s | 0.137 s | 0.268 s |
| Sol shared prefix | 0.220 s | 0.312 s | 0.166 s | 0.297 s |
| Sonnet shared prefix | 0.195 s | 0.376 s | 0.213 s | 0.424 s |
| Opus shared prefix | 0.954 s | 2.255 s | 0.806 s | 1.535 s |

The final Sonnet dispersion is close to the GPT sessions, whereas final Opus is
materially noisier. This is a session-level observation, not a general provider or
model-family property.

## 6. Chronological block design

A block is one chronological round containing exactly one request at each tested
context length. With a constant repetition count, the number of blocks equals the
number of observations per length. Context order is freshly shuffled inside every
block, and the next block begins after the prior one finishes.

Measured wall time per block—first request start through last request completion—was:

| Session | Requests per block | Median block duration | Range |
|---|---:|---:|---:|
| Terra | 9 | 50.705 s | 48.938–57.112 s |
| Sol | 6 | 46.495 s | 42.904–49.579 s |
| Sonnet | 8 | 51.116 s | 48.429–57.205 s |
| Opus | 8 | 81.897 s | 75.767–95.437 s |

This design interleaves short and long contexts through time. It avoids the obvious
confound that would occur if all short prompts ran first and all long prompts ran
later under a different load regime. In the regressions, block fixed effects give
each chronological round its own additive intercept while sharing the token-scaling
coefficients across blocks. They are intended to absorb block-wide faster/slower
conditions such as temporal load, routing regime, network conditions, scheduler
state, or cache-cohort state that affect all lengths in approximately additive
fashion.

Block effects cannot recover variables the API does not expose. They do not remove
within-block drift, request-specific queueing or batching, a context-length-by-load
interaction, or a routing change that affects only one request. Randomization and
fixed effects reduce time-order confounding; they do not isolate pure compute.

## 7. Measurement limitations

The public response metadata does not reveal:

- provider queue time;
- batch size or batching delay;
- worker, accelerator, host, cluster, or datacenter assignment;
- accelerator type or hardware generation;
- prompt-cache physical placement or transfer cost;
- concurrent tenant or request load;
- scheduler policy/state;
- internal retry, failover, or speculative execution behavior; or
- a decomposition of upload, cache lookup, prefill kernels, first-token decode, and
  return-path time.

The client additionally ran from one labeled home network, and the experiment did
not independently randomize geographic origin, account, organization, API tier, or
time of day. A persistent HTTP client reduces connection setup differences after
the preliminary count-token call, but it does not remove public-network variance.

Accordingly, the dependent variable is **effective end-to-end API TTFT under the
specified request and cache protocol**. Its scaling includes network and serving
system behavior. It is not an isolated measurement of model FLOPs, attention-kernel
runtime, GPU prefill time, or theoretical architectural complexity.

An additional reproducibility limitation is that session files do not include a
source-control commit or full command line, and this workspace has no repository
history. The session metadata and payload/results are sufficient to reconstruct the
effective design, but the sub-four-second Terra start intervals show why current
source should not be treated as a byte-exact historical revision where logs
contradict it.

## 8. Reproducibility table

| Parameter | GPT-5.6 Terra | GPT-5.6 Sol | Claude Sonnet 5 | Claude Opus 5 |
|---|---|---|---|---|
| Session ID | `20260813T155415Z-6998d614` | `20260814T140715Z-bee825d8` | `20260814T154718Z-5dc271b9` | `20260813T163222Z-b3406d60` |
| JSONL file | `data/raw/final/20260813T155415Z-6998d614.jsonl` | `data/raw/final/20260814T140715Z-bee825d8.jsonl` | `data/raw/final/20260814T154718Z-5dc271b9.jsonl` | `data/raw/final/20260813T163222Z-b3406d60.jsonl` |
| API endpoint | `/v1/responses` | `/v1/responses` | `/v1/messages` | `/v1/messages` |
| Model ID | `gpt-5.6-terra` | `gpt-5.6-sol` | `claude-sonnet-5` | `claude-opus-5` |
| Local measured time | Aug 13, 11:58–12:05 EDT | Aug 14, 10:09–10:13 EDT | Aug 14, 11:48–12:00 EDT | Aug 13, 12:33–12:42 EDT |
| Lengths (tokens) | 50k, 100k, 175k, 250k, 275k, 375k, 550k, 750k, 850k | 50k, 175k, 250k, 275k, 550k, 850k | 50k, 100k, 175k, 250k, 375k, 550k, 750k, 900k | same as Sonnet |
| Blocks × lengths | 8 × 9 | 5 × 6 | 14 × 8 | 6 × 8 |
| Valid measured requests | 72 | 30 | 112 | 48 |
| Execution | sequential, one persistent client/connection limit | same | same | same |
| Within-block order | randomized; exact order listed above | randomized | randomized | randomized |
| Configured start pacing | 4 s target | 4 s target | 4 s target | 4 s target |
| Observed median start interval | 4.014 s | 4.750 s | 4.387 s | 9.001 s |
| Output limit | 32 | 32 | 32 | 32 |
| Reasoning/thinking | effort `none`; 0 reasoning tokens observed | same | thinking `disabled`; 0 thinking blocks | same |
| Temperature/top-p | omitted | omitted | omitted | omitted |
| Streaming | SSE; TTFT at first nonempty OpenAI text delta | same | SSE; TTFT at first nonempty Anthropic text delta | same |
| Prefix requested / read | 2,048 / 2,051 | 2,048 / 2,051 | 2,048 / 2,052 | 2,048 / 2,052 |
| Cache control | explicit breakpoint + explicit-only mode + session cache key | same | ephemeral explicit breakpoint, 5-minute TTL | same |
| Setup excluded | yes, one cache-write generation | yes | yes | yes |
| Measured cache metadata | every row: read 2,051, write 0 | same | every row: read 2,052, write 0 | same |
| Actual total vs nominal | nominal − 2 | nominal − 2 | nominal − 6 | nominal − 6 |
| Fixed output | exact `OK` requested and observed | same | same | same |
| Leading uniqueness nonce | yes, in uncached continuation | yes | yes | yes |
| Corpus hash | `075768889cfef63bcbb967fa0204b6048201fdfe896124915f75e8dadc8b9e75` | same | same | same |
| Network label | `home-toronto` | same | same | same |

## Claims safe to use in the report

- The four finalized datasets contain 72 Terra, 30 Sol, 112 Sonnet, and 48 Opus
  valid sequential requests, organized as randomized chronological blocks with one
  request per context length per block.
- Every measured request reused one directly verified 2,051-token OpenAI or
  2,052-token Anthropic cached prefix while leaving approximately 48k–898k tokens as
  new input, depending on the target length.
- Provider usage metadata reported the expected cache read and zero cache writes on
  every finalized measured request.
- Reasoning was set to `none` for OpenAI and thinking to `disabled` for Anthropic;
  observed reasoning tokens/thinking blocks were zero.
- TTFT was timed from immediately before sending the serialized HTTP request to the
  first nonempty streamed text delta.
- Context lengths were randomized within blocks rather than run monotonically, and
  block fixed effects were used to account for additive chronological shifts.
- Early cache-miss Claude pilots contained large same-length dispersion, and some
  shared-prefix pilots had lower robust dispersion; the reduction was not uniform
  across lengths, sessions, or providers.
- The shared-prefix method does not eliminate latency noise: the finalized Opus
  shared-prefix run remained substantially noisier than the other three finalized
  sessions.
- The experiment measures effective API TTFT scaling, not isolated accelerator or
  model-kernel execution time.

## Interpretations that should remain qualified

- A reusable prefix may create cache/routing affinity and may narrow the serving
  cohort. OpenAI documents cache-key/prefix-hash routing, but the benchmark does not
  observe worker identity; Anthropic does not document an equivalent routing
  mechanism in the cited guide.
- Lower dispersion in some shared-prefix pilots is consistent with reduced routing
  heterogeneity, but it is not a controlled causal estimate of cache affinity.
- Different serving configurations, load, datacenters, cache placement, scheduler
  state, batching, or hardware generations could contribute to latency variation.
  The benchmark cannot distinguish among them.
- It is not supported to claim that same-prefix requests necessarily used the same
  accelerator, GPU node, CPU host, datacenter, or physical cache memory.
- It is not supported to claim from these sessions that Anthropic generally uses
  more heterogeneous hardware or that Claude is intrinsically noisier than GPT.
- The configured four-second pacing target should not be described as an invariant
  of the historical runs: the Terra and Sol timestamps include a small number of
  shorter start intervals.

## Artifact index

- Implementation: `src/ttft_bench/cli.py`
- Configuration: `config/benchmark.toml`
- Corpus manifest: `data/corpus/manifest.json`
- Experimental notes and estimator methodology:
  `docs/statistical-methodology.md`
- Final raw data: the four JSONL files listed in the reproducibility table
- Final plot data export: `outputs/tables/request_observations.csv`
