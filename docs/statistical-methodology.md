# Statistical methodology for the TTFT scaling analysis

This document is the full statistical record behind the shorter blog and
technical appendix. It describes the estimands, likelihoods, constraints,
resampling procedures, diagnostics, and interpretation limits used for the four
finalized sessions. The executable source of truth is `analysis/reproduce.R`.

## 1. Quantity being estimated

For request (i) in chronological block (j), let (y_{ij}) be observed time
to first text token in seconds and let

\[
x_i = \frac{\text{nominal target input tokens}_i}{10^6}.
\]

The common quadratic-capable serving curve is

\[
\mu_{ij}=\alpha+\beta x_i+\gamma x_i^2+\delta_j,
\qquad \sum_j\delta_j=0.
\]

The linear model is the nested case (gamma=0). The block effects represent
changes in the baseline latency over the course of a session. The plotted curve
sets all block columns to zero and is therefore the average-block curve under
sum coding.

The derivative of a quadratic curve is

\[
\frac{d\mu}{dx}=\beta+2\gamma x,
\]

in seconds per additional million tokens. The reported marginal seconds per
100,000 tokens divide this quantity by ten.

Nominal target length is used for (x). Provider-reported input was consistently
two tokens below nominal for OpenAI and six below nominal for Anthropic. These
fixed offsets have no material effect on curvature and using nominal length makes
the block design exact.

## 2. Serving-time interpretation

The working measurement model is

\[
\text{observed TTFT}
=\text{context-dependent serving curve}
+\text{small two-sided variation}
+\text{nonnegative contention delay}.
\]

This is a useful statistical decomposition, not a direct observation of serving
internals. The public APIs do not expose queue time, batching, worker identity,
hardware, cache placement, datacenter, or concurrent load. Consequently, the
curve describes effective public-API TTFT under the collection protocol. It is
not an estimate of isolated model FLOPs, attention-kernel time, or GPU prefill
runtime.

The three headline estimators intentionally target somewhat different levels:

- Student-t regression estimates a robust center of observed TTFT.
- Stochastic frontier estimates a latent lower serving curve after assigning
  every request a positive exponential delay.
- Spike plus contention estimates a latent lower serving curve while allowing
  some requests to have no contention delay.

Agreement about curvature is more important than agreement about intercepts.

## 3. Chronological blocks

Each finalized block contains one sequential request at every context length,
with length order shuffled inside the block. Requests in a block therefore share
approximately the same period of the collection session. Fixed effects are
intended to absorb slow changes in network or provider conditions that shift all
lengths in a block together.

The design matrix uses `contr.sum(K)` for a session with (K) blocks. It contains
(K-1) explicit coefficients; the final effect is the negative sum of those
coefficients. This parameterization makes the intercept the average-block
intercept. Changing contrast coding would not change fitted values or the
estimated (gamma).

The Student-t quadratic sensitivity estimates, in seconds per million tokens
squared, are:

| Model | Without block effects | With block effects |
|---|---:|---:|
| GPT-5.6 Terra | 7.7728254268 | 8.0264609654 |
| GPT-5.6 Sol | 10.4686646451 | 10.4159004407 |
| Claude Sonnet 5 | -0.1931542540 | -0.2058226436 |
| Claude Opus 5 | -0.2176524996 | 1.5753668681 |

The headline Terra, Sol, and Sonnet conclusions are insensitive to the block
terms. Opus is noisier and its point estimate is more sensitive, although its
linear-versus-quadratic conclusion remains unchanged. Joint likelihood-ratio
tests for all block effects give approximate p-values of 0.293, 0.124, 0.318,
and 0.070 for Terra, Sol, Sonnet, and Opus respectively. The block terms are a
design-based adjustment and precision safeguard rather than the source of the
headline result.

## 4. Student-t regression

The primary likelihood is

\[
y_{ij}\mid x_i,j \sim t_{\nu}(\mu_{ij},\sigma),
\qquad \nu=4.
\]

Both linear and quadratic versions estimate coefficients and positive scale
(sigma) by maximum likelihood. The quadratic coefficient is unconstrained, so
the model can estimate positive, zero, or negative curvature. A Huber regression
initializes the coefficients; the initial scale is the MAD of its residuals,
bounded below by (10^{-3}). BFGS then minimizes negative log likelihood with
`maxit = 2000` and `reltol = 1e-10`.

A Student-t likelihood reduces the influence of large residuals continuously.
It does not remove observations or classify individual requests as outliers.

### Linear-versus-quadratic comparisons

For each model, the reported likelihood-ratio statistic is

\[
2\Delta\log L=2(\log L_{quadratic}-\log L_{linear}).
\]

The conventional reference p-value uses a chi-squared distribution with one
degree of freedom because the unconstrained Student-t quadratic model adds one
parameter. AICc is

\[
\mathrm{AICc}=-2\log L+2k+\frac{2k(k+1)}{n-k-1},
\]

where (k) includes curve coefficients, block effects, and (sigma). Positive
`linear AICc - quadratic AICc` favors the quadratic model.

These likelihood comparisons describe the fitted Student-t specification. The
bootstrap curvature intervals below instead use Huber refits and should not be
called Student-t confidence intervals.

## 5. Huber whole-block bootstrap

The general robust curvature interval uses 5,000 quadratic Huber refits. The
pilot/refit is `MASS::rlm` with formula

```r
y ~ x + I(x^2) + block
```

and `psi = psi.huber`, `maxit = 200`. With the finalized MASS version, the tuning
constant is (k=1.345), method is M-estimation, initialization is least squares,
scale estimation is MAD, convergence tolerance is (10^{-4}), and the IRLS
weight is

\[
w(u)=\min(1,1.345/|u|).
\]

The Huber (gamma) is unconstrained. The formula fit uses R's default treatment
contrast inside the bootstrap; (gamma) and fitted values are invariant to this
choice because the same block subspace is represented.

For a dataset with (K) blocks, each replicate samples (K) whole original
blocks with replacement. Every request in a sampled block stays together. Each
draw is relabeled `boot_1` through `boot_K`, so two copies of the same original
block are represented as two separate bootstrap blocks.

One RNG stream begins with `set.seed(20260817)` and processes Terra, Sol, Sonnet,
and Opus in that order. Intervals are the 2.5th and 97.5th empirical percentiles
using R's default type-7 quantiles. `% gamma > 0` is the fraction of successful
replicates whose coefficient is strictly positive. All 5,000 replicates per
model succeeded in the finalized run.

Whole-block rather than request-level resampling preserves dependence among the
different context lengths observed during the same period.

## 6. Stochastic-frontier regression

The frontier model is

\[
y_{ij}=\mu_{ij}+\epsilon_{ij}+d_{ij},
\qquad \epsilon_{ij}\sim N(0,\sigma^2),
\qquad d_{ij}\sim\operatorname{Exponential}(\lambda).
\]

Every request receives a nonnegative modeled delay. Its mean is (1/\lambda).
The displayed (mu(x)) excludes this delay and represents the fitted latent
uncontended curve.

The intercept and block effects are unconstrained. The implementation constrains
(0\leq\beta\leq100) and (0\leq\gamma\leq100), with bounds expressed in the
million-token units above. The optimizer is L-BFGS-B with multiple robust starts,
`maxit = 3000`, `factr = 1e7`, and `pgtol = 1e-8`.

## 7. Spike-plus-contention regression

The mixture model is

\[
y_{ij}=\mu_{ij}+\epsilon_{ij}+C_{ij}d_{ij},
\]

\[
\epsilon_{ij}\sim N(0,\sigma^2),\quad
C_{ij}\sim\operatorname{Bernoulli}(\pi),\quad
d_{ij}\sim\operatorname{Exponential}(\lambda).
\]

With probability (1-\pi), a request is drawn from the narrow Gaussian clean
component. With probability (pi), it receives an additional exponential delay
whose conditional mean is (1/\lambda). The residual likelihood is therefore a
Gaussian/ex-Gaussian mixture.

The slope and curvature constraints and optimizer settings match the frontier
model. The fitted contention probability is constrained to the interval
[0.005, 0.995]. This is a model-based probability, not an observed fraction of
requests known to have queued.

## 8. Clean-scale anchor and sensitivity

An unrestricted mixture can increase likelihood by collapsing the clean
component toward zero width. The analysis therefore fixes (sigma) rather than
estimating it jointly.

For each dataset, a quadratic Huber pilot with sum-coded block effects produces
residuals (e_k). The anchor is

\[
\widehat\sigma=
\max\left(0.02,
\frac{\operatorname{median}(|e_k|:e_k\leq0)}{\Phi^{-1}(0.75)}
\right),
\]

where (Phi^{-1}(0.75)=0.6744897501960817). The negative side is used because
positive contention should contaminate it less strongly. The anchor is fixed
during each likelihood fit and recomputed from the resampled data inside every
asymmetric bootstrap replicate.

Spike and frontier fits are repeated with (0.5\widehat\sigma),
(widehat\sigma), and (2\widehat\sigma). These are specification-sensitivity
fits, not additional data.

## 9. Asymmetric-model uncertainty

Frontier and spike curvature intervals use 200 whole-block bootstrap replicates
per model and estimator, with `set.seed(20260819)`. Each replicate resamples and
relabels complete blocks exactly as above, recomputes the sigma anchor, and
refits the constrained quadratic likelihood.

The reported intervals are percentile intervals. Because (gamma\geq0), zero is
on the parameter-space boundary. The release therefore reports the fraction of
fits at the boundary and does not use a symmetric Wald interval or ordinary
chi-squared likelihood-ratio approximation for these estimators.

## 10. No observation deletion

Every valid measured request from each finalized session appears in the fits and
figures. High-latency requests are not removed. Robustness is obtained through:

1. heavy-tailed Student-t residuals;
2. bounded-influence Huber refits in the bootstrap;
3. explicit nonnegative-delay distributions in the frontier and mixture models;
4. chronological block effects and whole-block resampling.

Earlier exploratory analyses considered per-length 25th percentiles, one-sided
trimming, ordinary least squares, Tukey regression, and median polish. These
helped diagnose the noise but are not the authoritative estimators used by the
blog figures or final numerical tables.

## 11. Extrapolation

Figure 1 fits the same quadratic-capable Student-t model to all four datasets.
The separate extrapolation scenario uses quadratic Student-t fits for Terra and
Sol and linear Student-t fits for Sonnet and Opus. This choice is made only after
the within-range model comparison; it is not used to generate the empirical
comparison figure.

Extrapolations beyond approximately 0.9 million tokens are stress tests of the
estimated functional forms. They are not validated forecasts, and they do not
assert that future APIs will accept those contexts or retain the same serving
system. The Opus quadratic result and the all-four-quadratic table are retained
as sensitivity cases.

## 12. Reproducibility and numerical precision

The canonical script writes every coefficient, block effect, bootstrap summary,
bootstrap draw, extrapolation, and marginal-latency value to `outputs/`. Small
optimizer-level differences can occur across R, MASS, compiler, and BLAS
versions. The release pins the direct package versions used here and preserves
the authoritative generated tables so such differences can be detected rather
than silently substituted.

The analysis supports statements about the shape of effective API TTFT under the
measured protocol. It does not by itself identify the model architecture or
prove that requests shared a GPU, node, host, datacenter, or particular cache
memory tier.
