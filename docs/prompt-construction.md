# Exact prompt construction for the finalized TTFT benchmark

This document describes the prompt bytes and API content-block layout used in the
four finalized TTFT sessions. It is derived from
[`src/ttft_bench/cli.py`](../src/ttft_bench/cli.py),
[`config/benchmark.toml`](../config/benchmark.toml), the pinned
[`data/corpus/manifest.json`](../data/corpus/manifest.json), and the four JSONL session logs.
It supplements [`collection-methodology.md`](collection-methodology.md).

The concise description is:

> Each measured prompt had the logical form
> **[fixed cached prefix] [fresh per-request nonce] [fixed tail for that provider
> and context length]**. The cached prefix was identical at every context length
> and repetition within a session. A nonce was independently sampled for every
> request. Everything after the nonce was identical across repetitions at the
> same context length.

That statement is correct if “suffix” means the text **after** the nonce. The
nonce and suffix were transmitted together as one uncached API content block, so
calling the whole second content block “the fixed suffix” would be imprecise.

## 1. Formal construction

Let:

- `C` be the pinned combined Project Gutenberg corpus;
- `p` identify the provider tokenizer/prompt geometry;
- `s_p` be the provider-specific character offset where the cached prefix ends;
- `e_{p,L}` be the provider- and target-specific character offset where the
  included corpus ends for nominal context length `L`;
- `i` identify an individual request.

The text supplied to a measured request was constructed as:

```text
P_p     = "REFERENCE TEXT:\n" + C[0:s_p]

N_i     = "Benchmark nonce: "
          + " ".join(str(byte % 10) for byte in uuid.uuid4().bytes)
          + "\n"

S_{p,L} = C[s_p:e_{p,L}]
          + "\n\nTASK:\n"
          + "Do not think or analyze. Respond immediately with exactly one word: OK"

request_text_{p,L,i} = P_p || N_i || S_{p,L}
```

Here `||` denotes concatenation. `C[a:b]` uses Python Unicode-character indexes,
not byte or token indexes.

The construction therefore has three distinct invariants:

1. `P_p` is fixed across every measured request in the relevant sessions.
2. `N_i` is independently generated for every request.
3. `S_{p,L}` is fixed across all repetitions at the same provider and target
   length, but changes when the target length changes.

Only `P_p` was deliberately placed before a prompt-cache breakpoint. The nonce
and target-specific tail were after that breakpoint and were reported as new input
by both providers.

### What “nested prompts” means

For two targets `L1 < L2`, the corpus portion of the shorter tail is a prefix of
the corpus portion of the longer tail:

```text
C[s_p:e_{p,L1}] is a prefix of C[s_p:e_{p,L2}].
```

The complete tail `S_{p,L1}` is **not** a literal prefix of `S_{p,L2}`, because
the fixed `TASK` instruction is appended immediately after `e_{p,L1}` in the
shorter request but appears later in the longer request. The experiment reused a
nested corpus body rather than drawing a different document sample for each
length.

## 2. API message/block layout

Both providers received a single user message containing two text content blocks.
The boundary between those blocks was also the deliberate cache boundary.

### OpenAI: GPT-5.6 Terra and GPT-5.6 Sol

The material parts of each request to `POST /v1/responses` were:

```json
{
  "model": "gpt-5.6-terra or gpt-5.6-sol",
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "P_p",
          "prompt_cache_breakpoint": {"mode": "explicit"}
        },
        {
          "type": "input_text",
          "text": "N_i || S_{p,L}"
        }
      ]
    }
  ],
  "prompt_cache_options": {"mode": "explicit"},
  "prompt_cache_key": "ttft:shared:{session_id}:{model_id}",
  "reasoning": {"effort": "none"},
  "service_tier": "default",
  "max_output_tokens": 32,
  "stream": true,
  "store": false
}
```

The same `prompt_cache_key` was reused throughout one session. It changed between
sessions because the session ID and model ID were included in it. OpenAI's
[prompt-caching documentation](https://developers.openai.com/api/docs/guides/prompt-caching)
describes `prompt_cache_options.mode="explicit"` as using only explicitly marked
breakpoints and recommends placing changing content after the breakpoint. That is
the documented cache behavior the benchmark requested; it is separate from any
hypothesis about undocumented internal reuse.

### Anthropic: Claude Sonnet 5 and Claude Opus 5

The material parts of each request to `POST /v1/messages` were:

```json
{
  "model": "claude-sonnet-5 or claude-opus-5",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "P_p",
          "cache_control": {"type": "ephemeral", "ttl": "5m"}
        },
        {
          "type": "text",
          "text": "N_i || S_{p,L}"
        }
      ]
    }
  ],
  "thinking": {"type": "disabled"},
  "max_tokens": 32,
  "stream": true
}
```

Anthropic did not receive an application-supplied cache key. Its explicit
`cache_control` marker was attached only to the first text block. Anthropic's
[prompt-caching documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
states that the cache covers the exact prompt prefix through the marked block and
that input after the final breakpoint is reported as ordinary `input_tokens`.

## 3. Exact cached prefixes

The requested shared-prefix size was 2,048 provider tokens. The implementation
binary-searched a character boundary using each provider's token-count endpoint.
Because the tokenizers and request accounting differ, the two provider families
used different character boundaries in the same source corpus.

| Finalized models | `s_p` in corpus characters | UTF-8 bytes in `P_p` | Reported cache-read tokens | `stable_prefix_sha256` |
|---|---:|---:|---:|---|
| GPT-5.6 Terra and Sol | 9,454 | 9,500 | 2,051 | `730485e7e542bd012d1a7de896a57ef9d4048173bb8dcdc412e0127ef1738836` |
| Claude Sonnet 5 and Opus 5 | 6,347 | 6,381 | 2,052 | `ce8dc4f87e97c83ecc044c11b36a37bc895d11af4f881ee5ac55919cf192a477` |

The hash is over the exact UTF-8 encoding of:

```text
"REFERENCE TEXT:\n" + C[0:s_p]
```

The recovered split boundaries are:

```text
OpenAI:
"... distinctly feminine element in “Mr. Spectator,” and in\n"
| CACHE BREAKPOINT | "Jane Austen’s genius there was, though nothing man ..."

Anthropic:
"... Collins, the visit to Hunsford, the Derbyshire "
| CACHE BREAKPOINT | "tour--fit in after the\nsame unostentatious, but ma ..."
```

The OpenAI prefix was byte-identical between the finalized Terra and Sol
sessions. The Anthropic prefix was byte-identical between the finalized Sonnet
and Opus sessions. The OpenAI and Anthropic prefixes were not byte-identical to
one another because provider token counting selected different corpus split
points.

The reported 2,051/2,052 cache tokens should be treated as provider usage
accounting for the cached request prefix, not as an independently reproduced
tokenization of the raw text alone; message framing may contribute to provider
input accounting.

## 4. Exact target-specific corpus ranges and token accounting

The requested target length includes the cached prefix, nonce, corpus tail,
instruction, and any provider-counted message framing. It does not mean “target
new tokens plus a 2k prefix.” Almost all the context remained new input.

The character offsets below were recovered from the recorded prompt-template
hashes. At each target, every repetition had the same provider-reported actual
total, cache-read count, and new-input count.

### OpenAI prompt geometry

Terra used all rows below. Sol used 50k, 175k, 250k, 275k, 550k, and 850k. For
shared targets, Terra and Sol used the same corpus end offset.

| Nominal target | `e_{p,L}` corpus end | Corpus characters after cached split | Actual total input | Cache read | New input |
|---:|---:|---:|---:|---:|---:|
| 50,000 | 214,192 | 204,738 | 49,998 | 2,051 | 47,947 |
| 100,000 | 429,925 | 420,471 | 99,998 | 2,051 | 97,947 |
| 175,000 | 750,015 | 740,561 | 174,998 | 2,051 | 172,947 |
| 250,000 | 1,044,865 | 1,035,411 | 249,998 | 2,051 | 247,947 |
| 275,000 | 1,142,955 | 1,133,501 | 274,998 | 2,051 | 272,947 |
| 375,000 | 1,551,634 | 1,542,180 | 374,998 | 2,051 | 372,947 |
| 550,000 | 2,270,860 | 2,261,406 | 549,998 | 2,051 | 547,947 |
| 750,000 | 3,097,796 | 3,088,342 | 749,998 | 2,051 | 747,947 |
| 850,000 | 3,507,175 | 3,497,721 | 849,998 | 2,051 | 847,947 |

### Anthropic prompt geometry

Sonnet and Opus used the same eight target lengths and the same character ranges.

| Nominal target | `e_{p,L}` corpus end | Corpus characters after cached split | Actual total input | Cache read | New input |
|---:|---:|---:|---:|---:|---:|
| 50,000 | 146,856 | 140,509 | 49,994 | 2,052 | 47,942 |
| 100,000 | 293,384 | 287,037 | 99,994 | 2,052 | 97,942 |
| 175,000 | 517,031 | 510,684 | 174,994 | 2,052 | 172,942 |
| 250,000 | 738,062 | 731,715 | 249,994 | 2,052 | 247,942 |
| 375,000 | 1,082,332 | 1,075,985 | 374,994 | 2,052 | 372,942 |
| 550,000 | 1,579,804 | 1,573,457 | 549,994 | 2,052 | 547,942 |
| 750,000 | 2,146,359 | 2,140,012 | 749,994 | 2,052 | 747,942 |
| 900,000 | 2,589,836 | 2,583,489 | 899,994 | 2,052 | 897,942 |

The actual totals fell two tokens below nominal for OpenAI and six tokens below
nominal for Anthropic. The implementation selected the largest corpus character
offset whose sizing-time count did not exceed the target; it did not pad to an
exact token count. The sizing prompt also differed slightly from the measured
prompt, as described below. The finalized regressions use provider-reported
`total_input_tokens`, not the nominal target.

## 5. Nonce generation and placement

For every call to the generation endpoint, the code generated a new UUID4 and
mapped its 16 bytes independently into decimal digits:

```python
nonce = " ".join(str(byte % 10) for byte in uuid.uuid4().bytes)
```

An example with invented digits is:

```text
Benchmark nonce: 4 7 0 2 9 1 6 6 3 8 2 5 0 9 4 1
```

The nonce was placed immediately after the cached block and before any
target-dependent corpus continuation. It was not placed at the end of the prompt.
The implementation therefore freshly sampled the varying part of the second
content block on every call while keeping the first content block byte-identical.

The nonce values themselves were deliberately not written to the JSONL logs, so
historical nonce strings cannot be reconstructed from the result files. The logs
record `nonce_position="new_input_start"`. The code establishes independent nonce
generation, but exact historical uniqueness is not auditable because the nonce
values were not stored. A collision is possible in principle, although negligible
for the purpose of this experiment.

## 6. Prompt sizing versus the measured prompt

Prompt sizing and measurement used slightly different instruction/nonce layouts.
This distinction is important when interpreting nominal versus actual token counts
and the logged `prompt_sha256`.

During sizing, the token-count endpoint saw:

```text
[P_p]
[C[s_p:e_{p,L}]]

TASK:
Return exactly one short sentence summarizing the supplied text. Start immediately with the summary.
Benchmark nonce: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
```

During the measured generation, the generation endpoint saw:

```text
[P_p]
Benchmark nonce: {fresh UUID-derived digits}
[C[s_p:e_{p,L}]]

TASK:
Do not think or analyze. Respond immediately with exactly one word: OK
```

The final instruction was kept at the very end of the measured input. The
placeholder `Benchmark nonce:` label that the generic prompt builder normally put
at the end was removed in fixed-output mode.

The logged `prompt_sha256` is a preparation/template identifier. It hashes the
model ID, fixed prefix, and sizing-time suffix ending in the nonce label, before a
live nonce is inserted and before the fixed-`OK` instruction replaces the sizing
instruction. It is therefore useful for verifying one prepared geometry per
target, but it is **not** a hash of the exact request body sent on each measured
generation. The separate `stable_prefix_sha256` does hash the exact cached-prefix
text.

## 7. Cache setup and measured cache accounting

Before any measured request, the benchmark made one excluded `cache_setup`
generation. That request contained the same stable prefix block and a short
uncached nonce block, but no long corpus tail. It had to report:

- zero cache-read tokens; and
- a cache write of 2,051 tokens for OpenAI or 2,052 for Anthropic.

The benchmark then retained the very first measured cache hit; it did not discard
an inference warm-up. Every finalized measured request had to report:

| Provider | Cache read on every measured request | Cache write on every measured request |
|---|---:|---:|
| OpenAI | 2,051 | 0 |
| Anthropic | 2,052 | 0 |

It also checked that:

```text
new_input_tokens + cache_read_tokens + cache_write_tokens
    == total_input_tokens
```

Thus, according to the public API accounting, only the short `P_p` block was read
from prompt cache. The nonce and the entire long `S_{p,L}` tail were ordinary new
input on every measured request.

Token-count API calls were made while choosing `s_p` and `e_{p,L}`, so the text was
submitted to provider token-counting endpoints before the timed generation calls.
The subsequent cache-setup generation still reported a documented cache write,
not a read. This establishes that sizing did not pre-populate the documented
generation prompt cache. The public artifacts cannot establish whether a provider
shares any undocumented tokenization or preprocessing cache between its counting
and generation services.

## 8. Which text was shared at each comparison level?

| Comparison | Cached prefix `P_p` | Nonce `N_i` | Corpus portion of tail | Final instruction |
|---|---|---|---|---|
| Repetitions at the same length in one session | Identical | Freshly sampled; values not logged | Identical | Identical |
| Different lengths in one session | Identical | Freshly sampled; values not logged | Same starting point, different end | Identical |
| Terra versus Sol at a shared length | Identical text | Independently generated | Identical text | Identical |
| Sonnet versus Opus at a shared length | Identical text | Independently generated | Identical text | Identical |
| OpenAI versus Anthropic at the same nominal length | Different split point | Independently generated | Different split and end points | Identical |

Even where text was identical across models, the requests were not identical:
model identifiers differed, OpenAI cache keys were session-specific, and provider
message schemas/tokenization differed.

## 9. What this construction does and does not establish

The construction establishes the following directly:

- each finalized session deliberately reused one short, provider-verified cached
  prefix;
- almost all input tokens remained uncached and were processed as new input;
- every measured continuation received a freshly sampled nonce before the long
  repeated tail;
- repetitions at one length used the same post-nonce corpus text and instruction;
- all target lengths were derived from one pinned corpus rather than unrelated
  samples; and
- provider usage metadata did not report the long tail as a cache read or write.

It does not establish that the provider performed no undocumented reuse of the
repeated text after the nonce. In particular, public usage metadata describes the
documented prompt cache, not every possible internal tokenization, request-body,
preprocessing, routing, or storage optimization. Nor does the construction reveal
the worker, accelerator, host, datacenter, scheduler state, or cache placement.

The existing sessions can be inspected for a progressive latency decline as the
same tails are repeated, but they do not contain a randomized control arm whose
post-nonce corpus tail changes on every request. Consequently, the prompt design
is evidence that the long tail was billed and reported as new input, and it permits
an observational check for repeated-tail warming; it is not by itself a controlled
causal test excluding all hypothetical hidden suffix-cache effects.

## 10. Finalized session artifacts

| Model | Session ID | Result file |
|---|---|---|
| GPT-5.6 Terra | `20260813T155415Z-6998d614` | [`data/raw/final/20260813T155415Z-6998d614.jsonl`](../data/raw/final/20260813T155415Z-6998d614.jsonl) |
| GPT-5.6 Sol | `20260814T140715Z-bee825d8` | [`data/raw/final/20260814T140715Z-bee825d8.jsonl`](../data/raw/final/20260814T140715Z-bee825d8.jsonl) |
| Claude Sonnet 5 | `20260814T154718Z-5dc271b9` | [`data/raw/final/20260814T154718Z-5dc271b9.jsonl`](../data/raw/final/20260814T154718Z-5dc271b9.jsonl) |
| Claude Opus 5 | `20260813T163222Z-b3406d60` | [`data/raw/final/20260813T163222Z-b3406d60.jsonl`](../data/raw/final/20260813T163222Z-b3406d60.jsonl) |

The combined corpus SHA-256 recorded by all four sessions is:

```text
075768889cfef63bcbb967fa0204b6048201fdfe896124915f75e8dadc8b9e75
```
