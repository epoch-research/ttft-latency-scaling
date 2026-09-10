# Long-context API TTFT scaling

This repository contains the evidence and code behind the comparison of
long-context time-to-first-token (TTFT) scaling for GPT-5.6 Terra, GPT-5.6 Sol,
Claude Sonnet 5, and Claude Opus 5.

A separate [GPT-6 Astra API supplement](docs/astra-api.md) adds the September 9,
2026 measurements and an Astra-only Student-t plot. It does not replace or pool
with the original four-model results.

It supports two separate tasks:

1. **Offline reproduction:** refit the released observations and regenerate all
   reported tables, Figures 1–4, and the Astra supplement without API keys or paid requests.
2. **Fresh collection:** inspect or rerun the API protocol using your own keys,
   subject to current model availability, pricing, and provider behavior.

The fresh collector reproduces the experimental design. It cannot reproduce the
historical provider load, routing, queueing, cache placement, or hardware state
under which the archived observations were collected.

## Repository map

```text
analysis/             canonical fits, bootstraps, dispersion check, and figures
config/               API/model settings and final-session specifications
data/raw/final/        four sanitized finalized JSONL sessions
data/raw/supporting/   two uncached Sonnet sessions cited in the methodology
data/corpus/           exact combined Gutenberg corpus and hashes
data/prompts/          provider token-count cut points used by the collector
data/schedules/        observed request order for each released session
docs/                  collection, prompt, statistical, and numerical details
figures/               reproducible neutral Figures 1–4 in PNG, SVG, and PDF
outputs/               authoritative generated tables and bootstrap draws
data/raw/astra-api/     two sanitized Astra API logs (24 measurements + 2 setup requests)
outputs/astra-api/      independently regenerated Astra fit and observation tables
figures/astra-api/      additional neutral Astra-only plot
src/ttft_bench/        optional paid API collection client
```

The public logs retain all fields used by the analysis. See
[`data/REDACTION.md`](data/REDACTION.md) for the small set of operational
identifiers removed from the private originals.

## Reproduce the analysis

The recorded analysis environment used R 4.3.3 with MASS 7.3-60.0.1,
jsonlite 1.9.0, ggplot2 3.5.1, and scales 1.3.0. Direct versions are recorded in
`renv.lock`.

To restore those packages in a local R 4.3.3 installation:

```bash
Rscript -e 'install.packages("renv"); renv::restore()'
```

Run the public-data checks:

```bash
make validate
```

Regenerate all fits, the 5,000-replicate Huber bootstrap, the 200-replicate
frontier/mixture bootstraps, numerical documentation, and the four neutral
figures:

```bash
make reproduce
```

This workflow is offline. It does not read `.env` and cannot call either API.
To rerender figures quickly from the committed fit tables:

```bash
make figures
```

To reproduce only the Astra supplement, without paid requests:

```bash
make astra
```

This validates the release, refits Astra's linear and quadratic Student-t models,
and exports the Astra-only figure in PNG, SVG, and PDF. `make astra-figures`
rerenders it from committed tables. `make reproduce` also includes this supplement.
The original Figures 1–4 and their tables remain separate and unchanged.

The checked-in PNG, SVG, and PDF figures are generated directly by
`analysis/figures.R` using the included Inter font. Running `make figures`
recreates Figures 1–4 in place from the committed observations and fit tables;
`make astra-figures` recreates the additional Astra figure.
The plots are intentionally organization-neutral and contain no logo, branded
footer, or website asset.

## Statistical record

[`docs/statistical-methodology.md`](docs/statistical-methodology.md) is the full
technical record and is intentionally more detailed than the blog appendix. It
defines the Student-t, stochastic-frontier, and spike-plus-contention models;
block effects; sigma anchor; bootstrap implementation; model comparisons;
extrapolations; and interpretation limits.

Related documentation:

- [`docs/collection-methodology.md`](docs/collection-methodology.md)
- [`docs/prompt-construction.md`](docs/prompt-construction.md)
- [`docs/reproducibility-note.md`](docs/reproducibility-note.md)
- [`docs/results.md`](docs/results.md)

## Optional fresh API collection

Fresh collection is paid and is never part of `make reproduce`. Pricing in
`config/benchmark.toml` records the values used for the 2026 experiment and may
be stale. Confirm current prices and model availability before running anything.

Create a Python 3.12 environment and install the pinned client dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
cp .env.example .env
```

Put your own keys in `.env`. They are ignored by git. The included prompt files
and corpus are sufficient to reconstruct the requests; `prepare-prompts` is only
needed if you deliberately retokenize or add lengths.

First estimate a session without sending inference requests:

```bash
PYTHONPATH=src python -m ttft_bench.cli estimate \
  --models openai_terra \
  --lengths 50000,100000,175000,250000,275000,375000,550000,750000,850000 \
  --repetitions 8 \
  --shared-cache-prefix-tokens 2048 \
  --skip-warmup
```

An equivalent Terra rerun using the archived request order is:

```bash
PYTHONPATH=src python -m ttft_bench.cli run \
  --models openai_terra \
  --lengths 50000,100000,175000,250000,275000,375000,550000,750000,850000 \
  --repetitions 8 \
  --shared-cache-prefix-tokens 2048 \
  --shared-cache-min-interval-seconds 4 \
  --skip-warmup --fixed-output --leading-nonce \
  --schedule-file data/schedules/20260813T155415Z-6998d614.csv \
  --label terra-shared-prefix-scaling-rerun \
  --network-label YOUR_LOCATION \
  --max-cost-usd YOUR_REVIEWED_LIMIT
```

Equivalent model names, lengths, repetitions, and schedule paths for all four
sessions are in `config/final_sessions.json`. The client writes new data only to
the git-ignored `live-results/` directory. It validates the cache setup and each
measured hit, uses sequential streaming requests, disables reasoning/thinking,
and stops or marks a session partial if provider limits prevent completion.

## Measurement boundary

TTFT starts immediately before the prebuilt serialized HTTP request is sent and
ends at the first nonempty streamed text delta. It includes request upload,
network time, provider routing and queueing, cache lookup, prefill, first-token
generation, and return transit. It excludes local prompt assembly, token-count
calls, serialization, and request construction.

Accordingly, these results measure effective public-API serving latency under
the documented protocol—not isolated accelerator execution time.

## License

Except for the third-party materials identified in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), Epoch-authored contents of
this repository are available under the MIT License. See [`LICENSE`](LICENSE).
