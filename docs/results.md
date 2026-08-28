# Final authoritative TTFT results

Generated from the exact four sessions used in the finalized publication figures. Claude sessions are not pooled across days. `x` is measured in millions of target input tokens, and TTFT is measured in seconds.

## 1. Dataset metadata

| model | session_id | session_label | requests | chronological_blocks | minimum_total_input_tokens | maximum_total_input_tokens | target_context_lengths | exact_total_input_lengths | repetitions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 20260813T155415Z-6998d614 | terra-shared-prefix-scaling-large | 72 | 8 | 49998 | 849998 | 50000;100000;175000;250000;275000;375000;550000;750000;850000 | 49998;99998;174998;249998;274998;374998;549998;749998;849998 | 8 per context length |
| GPT-5.6 Sol | 20260814T140715Z-bee825d8 | sol-morning-shared-prefix-repeat | 30 | 5 | 49998 | 849998 | 50000;175000;250000;275000;550000;850000 | 49998;174998;249998;274998;549998;849998 | 5 per context length |
| Claude Sonnet 5 | 20260814T154718Z-5dc271b9 | sonnet-shared-prefix-more-blocks | 112 | 14 | 49994 | 899994 | 50000;100000;175000;250000;375000;550000;750000;900000 | 49994;99994;174994;249994;374994;549994;749994;899994 | 14 per context length |
| Claude Opus 5 | 20260813T163222Z-b3406d60 | opus-shared-prefix-scaling-large | 48 | 6 | 49994 | 899994 | 50000;100000;175000;250000;375000;550000;750000;900000 | 49994;99994;174994;249994;374994;549994;749994;899994 | 6 per context length |

All four sessions used a shared approximately 2,048-token cached prefix; the rest of each measured prompt was new input. Requests were sequential and each chronological block contained one request at every tested length.

## 2. Student-t linear fits

| model | alpha | beta | sigma | df | log_likelihood | nll | aicc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | -0.2774415976 | 12.63922922 | 0.5099748604 | 4 | -74.45479468 | 74.45479468 | 172.5161467 |
| GPT-5.6 Sol | -0.777487234 | 21.26908636 | 0.6929645026 | 4 | -38.61837461 | 38.61837461 | 96.32765831 |
| Claude Sonnet 5 | 0.4890076959 | 12.93758483 | 0.3044319778 | 4 | -61.77585334 | 61.77585334 | 161.2780225 |
| Claude Opus 5 | 1.602250679 | 21.79171658 | 1.493548661 | 4 | -100.5512032 | 100.5512032 | 220.7947141 |

The complete sum-to-zero block effects are reported in the machine-readable block-effect table at the end.

## 3. Student-t quadratic fits

| model | alpha | beta | gamma | sigma | df | log_likelihood | nll | aicc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 0.650893517 | 5.542573646 | 8.026460965 | 0.2328845212 | 4 | -35.3063083 | 35.3063083 | 97.01261659 |
| GPT-5.6 Sol | 0.5938947465 | 11.56570436 | 10.41590044 | 0.2827933877 | 4 | -18.09095775 | 18.09095775 | 59.03905835 |
| Claude Sonnet 5 | 0.4665486113 | 13.11846453 | -0.2058226436 | 0.3038994809 | 4 | -61.7070943 | 61.7070943 | 163.9248269 |
| Claude Opus 5 | 1.797532862 | 20.35960434 | 1.575366868 | 1.484432054 | 4 | -100.4775152 | 100.4775152 | 223.6918726 |

The finalized uncertainty interval for curvature is a 5,000-replicate whole-block bootstrap of a quadratic Huber refit. A separate Student-t MLE bootstrap was not part of the finalized analysis and is therefore not substituted here.

| model | two_log_likelihood_improvement | lr_p_value | huber_bootstrap_gamma_q025 | huber_bootstrap_gamma_median | huber_bootstrap_gamma_q975 | huber_bootstrap_fraction_gamma_positive |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 78.29697277 | 0.0000000000000000008865761942 | 6.820968092 | 8.122725975 | 9.121009429 | 1 |
| GPT-5.6 Sol | 41.05483373 | 0.0000000001480176433 | 8.972157299 | 10.3837005 | 13.03687324 | 1 |
| Claude Sonnet 5 | 0.1375180682 | 0.7107609622 | -1.222707591 | 0.02196308719 | 1.292407432 | 0.513 |
| Claude Opus 5 | 0.1473759399 | 0.7010557232 | -6.29689948 | 0.7914839063 | 9.698817473 | 0.555 |

## 4. Stochastic-frontier quadratic fits

| model | alpha | beta | gamma | sigma | lambda | mean_contention_delay_seconds | log_likelihood | nll | gamma_zero_boundary | any_parameter_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 0.3843668163 | 5.782014669 | 7.579355311 | 0.2298631393 | 2.358115347 | 0.4240674661 | -35.70985148 | 35.70985148 | FALSE | FALSE |
| GPT-5.6 Sol | 0.365913941 | 11.40352721 | 10.51503125 | 0.3302182861 | 2.341091557 | 0.427151171 | -18.46380236 | 18.46380236 | FALSE | FALSE |
| Claude Sonnet 5 | 0.252411272 | 12.73418841 | 0 | 0.2777123986 | 2.535212264 | 0.3944442895 | -62.66500129 | 62.66500129 | TRUE | TRUE |
| Claude Opus 5 | 0.3951790259 | 21.05143137 | 0.5977815039 | 1.283576661 | 0.6015510117 | 1.662369409 | -97.51923256 | 97.51923256 | FALSE | FALSE |

For the frontier model, every request has an exponential nonnegative delay, so the implied contention probability is 1 and the mean delay is `1/lambda`.

## 5. Spike-plus-contention quadratic fits

| model | alpha | beta | gamma | sigma | lambda | contention_probability | mean_contention_delay_seconds | log_likelihood | nll | gamma_zero_boundary | any_parameter_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 0.6218836888 | 5.668750704 | 7.760914759 | 0.2298631393 | 0.7901603463 | 0.1505417564 | 1.265565913 | -23.90162403 | 23.90162403 | FALSE | FALSE |
| GPT-5.6 Sol | 0.5231696806 | 11.82978129 | 10.16971808 | 0.3302182861 | 0.8330529254 | 0.1549442082 | 1.200403923 | -14.6739315 | 14.6739315 | FALSE | FALSE |
| Claude Sonnet 5 | 0.4912251403 | 12.65598849 | 0 | 0.2777123986 | 1.402719005 | 0.2614983849 | 0.7129011559 | -57.66006377 | 57.66006377 | TRUE | TRUE |
| Claude Opus 5 | 1.117212926 | 20.81536119 | 0.7781654727 | 1.283576661 | 0.4403931888 | 0.4359999014 | 2.270698152 | -96.63866694 | 96.63866694 | FALSE | FALSE |

`contention_probability` is pi. The mean delay conditional on contention is `1/lambda`. Sigma was anchored rather than estimated freely. The 0.5x and 2x sigma sensitivity fits, including gamma, appear below.

| model | estimator | sigma_multiplier | sigma | alpha | beta | gamma | lambda | contention_probability | mean_contention_delay_seconds | log_likelihood | nll | gamma_zero_boundary | any_parameter_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | Spike + contention | 0.5 | 0.1149315696 | 0.5069251549 | 6.017848306 | 7.151649031 | 1.522597572 | 0.4625551444 | 0.6567723597 | -25.07922485 | 25.07922485 | FALSE | FALSE |
| GPT-5.6 Terra | Spike + contention | 1 | 0.2298631393 | 0.6218836888 | 5.668750704 | 7.760914759 | 0.7901603463 | 0.1505417564 | 1.265565913 | -23.90162403 | 23.90162403 | FALSE | FALSE |
| GPT-5.6 Terra | Spike + contention | 2 | 0.4597262786 | 0.6447542075 | 5.937460044 | 7.425229644 | 0.5538345548 | 0.07649368535 | 1.80559337 | -42.35945633 | 42.35945633 | FALSE | FALSE |
| GPT-5.6 Sol | Spike + contention | 0.5 | 0.1651091431 | 0.5118137789 | 11.19856681 | 10.8752432 | 1.274358681 | 0.3604774887 | 0.7847084303 | -9.72982001 | 9.72982001 | FALSE | FALSE |
| GPT-5.6 Sol | Spike + contention | 1 | 0.3302182861 | 0.5231696806 | 11.82978129 | 10.16971808 | 0.8330529254 | 0.1549442082 | 1.200403923 | -14.6739315 | 14.6739315 | FALSE | FALSE |
| GPT-5.6 Sol | Spike + contention | 2 | 0.6604365723 | 0.7717446682 | 11.09416171 | 10.70104326 | 0.6709685887 | 0.06380362238 | 1.490382734 | -25.12529006 | 25.12529006 | FALSE | FALSE |
| Claude Sonnet 5 | Spike + contention | 0.5 | 0.1388561993 | 0.4339610019 | 12.22120631 | 0.1962069286 | 1.737409152 | 0.6389580244 | 0.575569663 | -53.29405773 | 53.29405773 | FALSE | FALSE |
| Claude Sonnet 5 | Spike + contention | 1 | 0.2777123986 | 0.4912251403 | 12.65598849 | 0 | 1.402719005 | 0.2614983849 | 0.7129011559 | -57.66006377 | 57.66006377 | TRUE | TRUE |
| Claude Sonnet 5 | Spike + contention | 2 | 0.5554247973 | 0.5137172042 | 12.96103807 | 0 | 0.2840891572 | 0.01244696771 | 3.520021706 | -73.07418248 | 73.07418248 | TRUE | TRUE |
| Claude Opus 5 | Spike + contention | 0.5 | 0.6417883304 | 1.375348702 | 15.45114641 | 6.382863387 | 0.3307774415 | 0.4955492548 | 3.023180769 | -89.39747398 | 89.39747398 | FALSE | FALSE |
| Claude Opus 5 | Spike + contention | 1 | 1.283576661 | 1.117212926 | 20.81536119 | 0.7781654727 | 0.4403931888 | 0.4359999014 | 2.270698152 | -96.63866694 | 96.63866694 | FALSE | FALSE |
| Claude Opus 5 | Spike + contention | 2 | 2.567153322 | 1.902360171 | 21.80965473 | 0 | 20 | 0.005 | 0.05 | -104.1257947 | 104.1257947 | TRUE | TRUE |

### Asymmetric-model curvature bootstrap

| model | estimator | requested | successful | gamma_q025 | gamma_median | gamma_q975 | fraction_gamma_positive | fraction_gamma_zero | fraction_any_parameter_boundary | gamma_constraint |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | Stochastic frontier | 200 | 200 | 6.648150805 | 7.427083025 | 8.548462624 | 1 | 0 | 0.02 | gamma >= 0 |
| GPT-5.6 Terra | Spike + contention | 200 | 200 | 6.268396397 | 7.677811177 | 8.850298927 | 1 | 0 | 0.005 | gamma >= 0 |
| GPT-5.6 Sol | Stochastic frontier | 200 | 200 | 9.340435149 | 10.56857611 | 12.6436211 | 1 | 0 | 0.03 | gamma >= 0 |
| GPT-5.6 Sol | Spike + contention | 200 | 200 | 9.313096893 | 10.3200171 | 11.02920633 | 1 | 0 | 0.025 | gamma >= 0 |
| Claude Sonnet 5 | Stochastic frontier | 200 | 200 | 0 | 0.01095501703 | 0.9281022537 | 0.51 | 0.49 | 0.49 | gamma >= 0 |
| Claude Sonnet 5 | Spike + contention | 200 | 200 | 0 | 0 | 1.033683817 | 0.39 | 0.61 | 0.65 | gamma >= 0 |
| Claude Opus 5 | Stochastic frontier | 200 | 200 | 0 | 0.7550940589 | 8.332164916 | 0.555 | 0.445 | 0.455 | gamma >= 0 |
| Claude Opus 5 | Spike + contention | 200 | 200 | 0 | 0.7776576091 | 8.24217689 | 0.545 | 0.455 | 0.465 | gamma >= 0 |

## 6. Linear-versus-quadratic conclusion

| model | two_log_likelihood_improvement | lr_p_value | delta_aicc_linear_minus_quadratic | student_t_gamma | huber_bootstrap_gamma_q025 | huber_bootstrap_gamma_q975 | huber_bootstrap_fraction_gamma_positive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 78.29697277 | 0.0000000000000000008865761942 | 75.50353015 | 8.026460965 | 6.820968092 | 9.121009429 | 1 |
| GPT-5.6 Sol | 41.05483373 | 0.0000000001480176433 | 37.28859996 | 10.41590044 | 8.972157299 | 13.03687324 | 1 |
| Claude Sonnet 5 | 0.1375180682 | 0.7107609622 | -2.64680444 | -0.2058226436 | -1.222707591 | 1.292407432 | 0.513 |
| Claude Opus 5 | 0.1473759399 | 0.7010557232 | -2.897158473 | 1.575366868 | -6.29689948 | 9.698817473 | 0.555 |

Numerically: Terra and Sol have large positive likelihood improvements and 5,000/5,000 positive Huber-bootstrap curvature estimates. Sonnet and Opus have likelihood-ratio p-values near 0.71 and 0.70 respectively, negative AICc improvements, bootstrap intervals spanning zero, and positive-curvature fractions near one half. This states only the statistical comparison.

## 7. Extrapolation values

The primary scenario uses quadratic Student-t fits for Terra and Sol and linear Student-t fits for Sonnet and Opus. Values beyond the approximately 0.9M measured range are illustrative extrapolations, not empirical API latency measurements.

| scenario | model | student_t_degree | input_tokens | ttft_seconds | ttft_minutes |
| --- | --- | --- | --- | --- | --- |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Terra | 2 | 1000000 | 14.21992813 | 0.2369988021 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Terra | 2 | 2000000 | 43.84188467 | 0.7306980779 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Terra | 2 | 5000000 | 229.0252859 | 3.817088098 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Terra | 2 | 10000000 | 858.7227265 | 14.31204544 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Sol | 2 | 1000000 | 22.57549954 | 0.3762583257 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Sol | 2 | 2000000 | 65.38890522 | 1.089815087 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Sol | 2 | 5000000 | 318.8199276 | 5.313665459 |
| Primary: quadratic GPT, linear Claude | GPT-5.6 Sol | 2 | 10000000 | 1157.840982 | 19.29734971 |
| Primary: quadratic GPT, linear Claude | Claude Sonnet 5 | 1 | 1000000 | 13.42659253 | 0.2237765421 |
| Primary: quadratic GPT, linear Claude | Claude Sonnet 5 | 1 | 2000000 | 26.36417736 | 0.439402956 |
| Primary: quadratic GPT, linear Claude | Claude Sonnet 5 | 1 | 5000000 | 65.17693185 | 1.086282198 |
| Primary: quadratic GPT, linear Claude | Claude Sonnet 5 | 1 | 10000000 | 129.864856 | 2.164414267 |
| Primary: quadratic GPT, linear Claude | Claude Opus 5 | 1 | 1000000 | 23.39396726 | 0.3898994543 |
| Primary: quadratic GPT, linear Claude | Claude Opus 5 | 1 | 2000000 | 45.18568384 | 0.7530947306 |
| Primary: quadratic GPT, linear Claude | Claude Opus 5 | 1 | 5000000 | 110.5608336 | 1.84268056 |
| Primary: quadratic GPT, linear Claude | Claude Opus 5 | 1 | 10000000 | 219.5194165 | 3.658656941 |

### Opus quadratic Student-t sensitivity

| scenario | model | student_t_degree | input_tokens | ttft_seconds | ttft_minutes |
| --- | --- | --- | --- | --- | --- |
| Opus quadratic sensitivity | Claude Opus 5 | 2 | 1000000 | 23.73250407 | 0.3955417344 |
| Opus quadratic sensitivity | Claude Opus 5 | 2 | 2000000 | 48.81820901 | 0.8136368168 |
| Opus quadratic sensitivity | Claude Opus 5 | 2 | 5000000 | 142.9797262 | 2.382995437 |
| Opus quadratic sensitivity | Claude Opus 5 | 2 | 10000000 | 362.930263 | 6.048837717 |

### All-four-quadratic Student-t sensitivity

| scenario | model | student_t_degree | input_tokens | ttft_seconds | ttft_minutes |
| --- | --- | --- | --- | --- | --- |
| Sensitivity: quadratic all models | GPT-5.6 Terra | 2 | 1000000 | 14.21992813 | 0.2369988021 |
| Sensitivity: quadratic all models | GPT-5.6 Terra | 2 | 2000000 | 43.84188467 | 0.7306980779 |
| Sensitivity: quadratic all models | GPT-5.6 Terra | 2 | 5000000 | 229.0252859 | 3.817088098 |
| Sensitivity: quadratic all models | GPT-5.6 Terra | 2 | 10000000 | 858.7227265 | 14.31204544 |
| Sensitivity: quadratic all models | GPT-5.6 Sol | 2 | 1000000 | 22.57549954 | 0.3762583257 |
| Sensitivity: quadratic all models | GPT-5.6 Sol | 2 | 2000000 | 65.38890522 | 1.089815087 |
| Sensitivity: quadratic all models | GPT-5.6 Sol | 2 | 5000000 | 318.8199276 | 5.313665459 |
| Sensitivity: quadratic all models | GPT-5.6 Sol | 2 | 10000000 | 1157.840982 | 19.29734971 |
| Sensitivity: quadratic all models | Claude Sonnet 5 | 2 | 1000000 | 13.37919049 | 0.2229865082 |
| Sensitivity: quadratic all models | Claude Sonnet 5 | 2 | 2000000 | 25.88018709 | 0.4313364515 |
| Sensitivity: quadratic all models | Claude Sonnet 5 | 2 | 5000000 | 60.91330515 | 1.015221752 |
| Sensitivity: quadratic all models | Claude Sonnet 5 | 2 | 10000000 | 111.0689295 | 1.851148825 |
| Sensitivity: quadratic all models | Claude Opus 5 | 2 | 1000000 | 23.73250407 | 0.3955417344 |
| Sensitivity: quadratic all models | Claude Opus 5 | 2 | 2000000 | 48.81820901 | 0.8136368168 |
| Sensitivity: quadratic all models | Claude Opus 5 | 2 | 5000000 | 142.9797262 | 2.382995437 |
| Sensitivity: quadratic all models | Claude Opus 5 | 2 | 10000000 | 362.930263 | 6.048837717 |

## 8. Marginal latency from every quadratic Student-t fit

For `x` in millions of tokens, `dTTFT/dx = beta + 2*gamma*x` gives seconds per additional million tokens. The final column divides this by 10 to report seconds of additional TTFT per additional 100k tokens.

| model | input_tokens | beta_seconds_per_million_tokens | gamma_seconds_per_million_tokens_squared | derivative_seconds_per_million_tokens | additional_seconds_per_100k_tokens |
| --- | --- | --- | --- | --- | --- |
| GPT-5.6 Terra | 100000 | 5.542573646 | 8.026460965 | 7.14786584 | 0.714786584 |
| GPT-5.6 Terra | 272000 | 5.542573646 | 8.026460965 | 9.908968412 | 0.9908968412 |
| GPT-5.6 Terra | 500000 | 5.542573646 | 8.026460965 | 13.56903461 | 1.356903461 |
| GPT-5.6 Terra | 900000 | 5.542573646 | 8.026460965 | 19.99020338 | 1.999020338 |
| GPT-5.6 Terra | 1000000 | 5.542573646 | 8.026460965 | 21.59549558 | 2.159549558 |
| GPT-5.6 Terra | 2000000 | 5.542573646 | 8.026460965 | 37.64841751 | 3.764841751 |
| GPT-5.6 Terra | 5000000 | 5.542573646 | 8.026460965 | 85.8071833 | 8.58071833 |
| GPT-5.6 Terra | 10000000 | 5.542573646 | 8.026460965 | 166.071793 | 16.6071793 |
| GPT-5.6 Sol | 100000 | 11.56570436 | 10.41590044 | 13.64888445 | 1.364888445 |
| GPT-5.6 Sol | 272000 | 11.56570436 | 10.41590044 | 17.2319542 | 1.72319542 |
| GPT-5.6 Sol | 500000 | 11.56570436 | 10.41590044 | 21.9816048 | 2.19816048 |
| GPT-5.6 Sol | 900000 | 11.56570436 | 10.41590044 | 30.31432515 | 3.031432515 |
| GPT-5.6 Sol | 1000000 | 11.56570436 | 10.41590044 | 32.39750524 | 3.239750524 |
| GPT-5.6 Sol | 2000000 | 11.56570436 | 10.41590044 | 53.22930612 | 5.322930612 |
| GPT-5.6 Sol | 5000000 | 11.56570436 | 10.41590044 | 115.7247088 | 11.57247088 |
| GPT-5.6 Sol | 10000000 | 11.56570436 | 10.41590044 | 219.8837132 | 21.98837132 |
| Claude Sonnet 5 | 100000 | 13.11846453 | -0.2058226436 | 13.0773 | 1.30773 |
| Claude Sonnet 5 | 272000 | 13.11846453 | -0.2058226436 | 13.00649701 | 1.300649701 |
| Claude Sonnet 5 | 500000 | 13.11846453 | -0.2058226436 | 12.91264188 | 1.291264188 |
| Claude Sonnet 5 | 900000 | 13.11846453 | -0.2058226436 | 12.74798377 | 1.274798377 |
| Claude Sonnet 5 | 1000000 | 13.11846453 | -0.2058226436 | 12.70681924 | 1.270681924 |
| Claude Sonnet 5 | 2000000 | 13.11846453 | -0.2058226436 | 12.29517395 | 1.229517395 |
| Claude Sonnet 5 | 5000000 | 13.11846453 | -0.2058226436 | 11.06023809 | 1.106023809 |
| Claude Sonnet 5 | 10000000 | 13.11846453 | -0.2058226436 | 9.002011654 | 0.9002011654 |
| Claude Opus 5 | 100000 | 20.35960434 | 1.575366868 | 20.67467771 | 2.067467771 |
| Claude Opus 5 | 272000 | 20.35960434 | 1.575366868 | 21.21660391 | 2.121660391 |
| Claude Opus 5 | 500000 | 20.35960434 | 1.575366868 | 21.9349712 | 2.19349712 |
| Claude Opus 5 | 900000 | 20.35960434 | 1.575366868 | 23.1952647 | 2.31952647 |
| Claude Opus 5 | 1000000 | 20.35960434 | 1.575366868 | 23.51033807 | 2.351033807 |
| Claude Opus 5 | 2000000 | 20.35960434 | 1.575366868 | 26.66107181 | 2.666107181 |
| Claude Opus 5 | 5000000 | 20.35960434 | 1.575366868 | 36.11327302 | 3.611327302 |
| Claude Opus 5 | 10000000 | 20.35960434 | 1.575366868 | 51.8669417 | 5.18669417 |

## 9. Exact fitting conventions

- `x = target_tokens / 1e6`; alpha is seconds, beta is seconds per million tokens, and gamma is seconds per million tokens squared.
- Student-t residual degrees of freedom were fixed at 4. Alpha, beta, gamma, and block effects were unconstrained; sigma was positive through a log-sigma parameterization.
- Student-t fits used maximum likelihood via R `optim(method = "BFGS", maxit = 2000, reltol = 1e-10)`, initialized from `MASS::rlm` with Huber loss and a MAD residual scale.
- Chronological block effects used `contr.sum(K)`: K-1 explicit coefficients plus a final effect equal to the negative sum, making the reported alpha the average-block intercept.
- The finalized general curvature interval resampled whole chronological blocks with replacement and refitted quadratic Huber regression 5,000 times (`set.seed(20260817)`). Requests within a selected block stayed together.
- The frontier and spike curvature intervals below used the same whole-block resampling logic for 200 replicates (`set.seed(20260819)`), re-estimating the sigma anchor in every replicate.
- For frontier and spike fits, beta and gamma were constrained to [0, 100], alpha to [-50, 50], block coefficients to [-100, 100], lambda to [0.01, 20], and spike pi to [0.005, 0.995].
- The clean-sigma anchor was `max(0.02, median(abs(r[r <= 0])) / qnorm(0.75))`, where `r` came from a quadratic Huber fit with sum-coded block effects. This is a fixed anchor, not a likelihood penalty. Sensitivities used 0.5 and 2 times this anchor.
- Frontier/spike optimization used R `optim(method = "L-BFGS-B", maxit = 3000, factr = 1e7, pgtol = 1e-8)`. Spike fits used starts at pi = 0.1, 0.35, 0.7, and 0.9 and retained the lowest NLL.
- Student-t linear-versus-quadratic LR statistics used one additional unconstrained gamma parameter and a chi-square(1) reference distribution.

## Machine-readable tables

### Dataset metadata

```csv
"model","session_id","session_label","requests","chronological_blocks","minimum_total_input_tokens","maximum_total_input_tokens","target_context_lengths","exact_total_input_lengths","repetitions"
"GPT-5.6 Terra","20260813T155415Z-6998d614","terra-shared-prefix-scaling-large",72,8,49998,849998,"50000;100000;175000;250000;275000;375000;550000;750000;850000","49998;99998;174998;249998;274998;374998;549998;749998;849998","8 per context length"
"GPT-5.6 Sol","20260814T140715Z-bee825d8","sol-morning-shared-prefix-repeat",30,5,49998,849998,"50000;175000;250000;275000;550000;850000","49998;174998;249998;274998;549998;849998","5 per context length"
"Claude Sonnet 5","20260814T154718Z-5dc271b9","sonnet-shared-prefix-more-blocks",112,14,49994,899994,"50000;100000;175000;250000;375000;550000;750000;900000","49994;99994;174994;249994;374994;549994;749994;899994","14 per context length"
"Claude Opus 5","20260813T163222Z-b3406d60","opus-shared-prefix-scaling-large",48,6,49994,899994,"50000;100000;175000;250000;375000;550000;750000;900000","49994;99994;174994;249994;374994;549994;749994;899994","6 per context length"
```

### All fit coefficients

```csv
"model","estimator","degree","alpha","beta","gamma","sigma","df","lambda","contention_probability","mean_contention_delay_seconds","log_likelihood","nll","aicc","convergence","gamma_zero_boundary","any_parameter_boundary"
"GPT-5.6 Terra","Student-t",1,-0.277441597575468,12.6392292167747,0,0.50997486035111,4,,,,-74.4547946810192,74.4547946810192,172.516146739088,0,FALSE,FALSE
"GPT-5.6 Terra","Student-t",2,0.650893516967782,5.54257364645402,8.02646096536283,0.23288452118613,4,,,,-35.3063082951718,35.3063082951718,97.0126165903436,0,FALSE,FALSE
"GPT-5.6 Sol","Student-t",1,-0.777487233987506,21.2690863647681,0,0.692964502647468,4,,,,-38.6183746099002,38.6183746099002,96.3276583107096,0,FALSE,FALSE
"GPT-5.6 Sol","Student-t",2,0.593894746533684,11.5657043572341,10.415900440701,0.282793387703336,4,,,,-18.0909577450025,18.0909577450025,59.0390583471478,0,FALSE,FALSE
"Claude Sonnet 5","Student-t",1,0.489007695933237,12.9375848309016,0,0.304431977848588,4,,,,-61.7758533378969,61.7758533378969,161.278022465267,0,FALSE,FALSE
"Claude Sonnet 5","Student-t",2,0.466548611266399,13.1184645251258,-0.20582264355797,0.303899480860015,4,,,,-61.7070943038001,61.7070943038001,163.924826905473,0,FALSE,FALSE
"Claude Opus 5","Student-t",1,1.60225067920375,21.7917165788098,0,1.49354866050795,4,,,,-100.551203194296,100.551203194296,220.794714080899,0,FALSE,FALSE
"Claude Opus 5","Student-t",2,1.79753286239863,20.3596043353143,1.57536686814213,1.48443205426827,4,,,,-100.477515224352,100.477515224352,223.691872553968,0,FALSE,FALSE
"GPT-5.6 Terra","Stochastic frontier",2,0.384366816282159,5.78201466854266,7.57935531131049,0.229863139297879,,2.35811534684174,1,0.424067466139566,-35.7098514835679,35.7098514835679,,0,FALSE,FALSE
"GPT-5.6 Terra","Spike + contention",2,0.621883688810983,5.66875070404015,7.76091475921591,0.229863139297879,,0.790160346305244,0.150541756385702,1.26556591288839,-23.9016240317038,23.9016240317038,,0,FALSE,FALSE
"GPT-5.6 Sol","Stochastic frontier",2,0.365913941004754,11.403527207433,10.5150312535429,0.330218286132028,,2.34109155681363,1,0.42715117103795,-18.4638023567059,18.4638023567059,,0,FALSE,FALSE
"GPT-5.6 Sol","Spike + contention",2,0.52316968062397,11.8297812873809,10.1697180829468,0.330218286132028,,0.833052925441708,0.154944208236985,1.20040392327987,-14.6739314986812,14.6739314986812,,0,FALSE,FALSE
"Claude Sonnet 5","Stochastic frontier",2,0.252411271959282,12.7341884080548,0,0.27771239862935,,2.53521226358529,1,0.394444289483597,-62.6650012946589,62.6650012946589,,0,TRUE,TRUE
"Claude Sonnet 5","Spike + contention",2,0.491225140346504,12.6559884862844,0,0.27771239862935,,1.4027190048845,0.261498384934546,0.712901155910654,-57.6600637661387,57.6600637661387,,0,TRUE,TRUE
"Claude Opus 5","Stochastic frontier",2,0.395179025881158,21.0514313669516,0.597781503935594,1.28357666079336,,0.601551011715474,1,1.66236940928459,-97.5192325579967,97.5192325579967,,0,FALSE,FALSE
"Claude Opus 5","Spike + contention",2,1.1172129262983,20.8153611917452,0.778165472677883,1.28357666079336,,0.440393188846358,0.43599990142775,2.27069815184829,-96.638666938007,96.638666938007,,0,FALSE,FALSE
```

### Block-effect coefficients

```csv
"model","estimator","block","effect_seconds","coefficient_status"
"GPT-5.6 Terra","Student-t degree 1","1",0.0341833220473882,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","2",-0.171427699622624,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","3",0.209445336723455,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","4",0.0343581894124989,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","5",0.0206458396738779,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","6",-0.122005978893037,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","7",0.0517063671009711,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 1","8",-0.0569053764425301,"implied as negative sum of explicit effects"
"GPT-5.6 Terra","Student-t degree 2","1",-0.0581912618672565,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","2",-0.0999606106998105,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","3",0.255229141598442,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","4",-0.107572986309113,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","5",0.0651173156282688,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","6",-0.0470025892830345,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","7",-0.0215208609601678,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Student-t degree 2","8",0.0139018518926711,"implied as negative sum of explicit effects"
"GPT-5.6 Sol","Student-t degree 1","1",-0.417324787894968,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 1","2",-0.208799775831239,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 1","3",0.335083363241948,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 1","4",-0.10705232784541,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 1","5",0.398093528329669,"implied as negative sum of explicit effects"
"GPT-5.6 Sol","Student-t degree 2","1",-0.24366844720587,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 2","2",-0.152841521447675,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 2","3",0.179685638213525,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 2","4",-0.01925749566244,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Student-t degree 2","5",0.23608182610246,"implied as negative sum of explicit effects"
"Claude Sonnet 5","Student-t degree 1","1",-0.0409412908597607,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","2",0.13344876353167,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","3",-0.131515001023327,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","4",-0.0845274684629731,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","5",0.40080698043562,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","6",0.039114711799016,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","7",-0.0562148588672882,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","8",-0.079404526984807,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","9",-0.0549564925567159,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","10",0.00396031102354756,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","11",0.150954599890643,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","12",-0.125196502076863,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","13",-0.188652196028074,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 1","14",0.0331229701793122,"implied as negative sum of explicit effects"
"Claude Sonnet 5","Student-t degree 2","1",-0.0421880221201822,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","2",0.133437159468123,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","3",-0.130992111933666,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","4",-0.0801631794652408,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","5",0.407632265030429,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","6",0.0370186970971363,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","7",-0.0577267015357908,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","8",-0.0805781295034837,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","9",-0.059713975063017,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","10",0.00133049436787152,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","11",0.147077415101147,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","12",-0.122731778411126,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","13",-0.186690195248942,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Student-t degree 2","14",0.0342880622167425,"implied as negative sum of explicit effects"
"Claude Opus 5","Student-t degree 1","1",0.615474395954663,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 1","2",-0.165418975821227,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 1","3",-0.974457667828092,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 1","4",1.77575419889987,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 1","5",-0.124029937253232,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 1","6",-1.12732201395198,"implied as negative sum of explicit effects"
"Claude Opus 5","Student-t degree 2","1",0.6345983809,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 2","2",-0.196167571392804,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 2","3",-0.961194308257246,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 2","4",1.85706859497653,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 2","5",-0.174001823872435,"explicit sum-contrast coefficient"
"Claude Opus 5","Student-t degree 2","6",-1.16030327235405,"implied as negative sum of explicit effects"
"GPT-5.6 Terra","Stochastic frontier","1",0.018732156170403,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","2",-0.171448397324825,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","3",0.161071487066341,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","4",-0.0744498992128776,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","5",0.0622511062100212,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","6",0.00464846439935011,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","7",-0.0112005527356006,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Stochastic frontier","8",0.0103956354271875,"implied as negative sum of explicit effects"
"GPT-5.6 Terra","Spike + contention","1",-0.0746309962363639,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","2",-0.121472200861735,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","3",0.223646359003015,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","4",-0.0822599136009392,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","5",0.0842344758971156,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","6",-0.0481724520195323,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","7",-0.0116834865816479,"explicit sum-contrast coefficient"
"GPT-5.6 Terra","Spike + contention","8",0.030338214400088,"implied as negative sum of explicit effects"
"GPT-5.6 Sol","Stochastic frontier","1",-0.248797537295521,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Stochastic frontier","2",-0.186386844116188,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Stochastic frontier","3",0.174315881055253,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Stochastic frontier","4",-0.0244576780920965,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Stochastic frontier","5",0.285326178448552,"implied as negative sum of explicit effects"
"GPT-5.6 Sol","Spike + contention","1",-0.265580253298775,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Spike + contention","2",-0.142394606950684,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Spike + contention","3",0.165780483220026,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Spike + contention","4",-0.00529257567789439,"explicit sum-contrast coefficient"
"GPT-5.6 Sol","Spike + contention","5",0.247486952707328,"implied as negative sum of explicit effects"
"Claude Sonnet 5","Stochastic frontier","1",0.0202165543573071,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","2",0.0967780524004535,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","3",-0.16897068455764,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","4",-0.0767711310434876,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","5",0.246479919723991,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","6",0.0689756384386837,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","7",-0.00668640156222027,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","8",-0.125372132100541,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","9",-0.101385796329481,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","10",-0.0181591166947935,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","11",0.166010852490214,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","12",-0.0652512011697061,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","13",-0.126375016727259,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Stochastic frontier","14",0.0905104627744777,"implied as negative sum of explicit effects"
"Claude Sonnet 5","Spike + contention","1",0.0222355802501599,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","2",0.0325905133333143,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","3",-0.149179698347219,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","4",-0.0418529930244777,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","5",0.264989083995553,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","6",0.0543148403403973,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","7",-0.00654114348534732,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","8",-0.131473454669568,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","9",-0.0585123279205795,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","10",-0.0226904584902427,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","11",0.126274111124877,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","12",-0.073591464369608,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","13",-0.112155196354288,"explicit sum-contrast coefficient"
"Claude Sonnet 5","Spike + contention","14",0.0955926076170277,"implied as negative sum of explicit effects"
"Claude Opus 5","Stochastic frontier","1",0.768505672169448,"explicit sum-contrast coefficient"
"Claude Opus 5","Stochastic frontier","2",0.0654528551578265,"explicit sum-contrast coefficient"
"Claude Opus 5","Stochastic frontier","3",-0.720974078387725,"explicit sum-contrast coefficient"
"Claude Opus 5","Stochastic frontier","4",0.866714613538876,"explicit sum-contrast coefficient"
"Claude Opus 5","Stochastic frontier","5",-0.0562760808428776,"explicit sum-contrast coefficient"
"Claude Opus 5","Stochastic frontier","6",-0.923422981635548,"implied as negative sum of explicit effects"
"Claude Opus 5","Spike + contention","1",0.784732870108963,"explicit sum-contrast coefficient"
"Claude Opus 5","Spike + contention","2",0.0854265646231055,"explicit sum-contrast coefficient"
"Claude Opus 5","Spike + contention","3",-0.684489564343973,"explicit sum-contrast coefficient"
"Claude Opus 5","Spike + contention","4",0.676194049938993,"explicit sum-contrast coefficient"
"Claude Opus 5","Spike + contention","5",0.00204194191987259,"explicit sum-contrast coefficient"
"Claude Opus 5","Spike + contention","6",-0.86390586224696,"implied as negative sum of explicit effects"
```

### Bootstrap intervals

```csv
"model","estimator","requested","successful","gamma_q025","gamma_median","gamma_q975","fraction_gamma_positive","fraction_gamma_zero","fraction_any_parameter_boundary","gamma_constraint"
"GPT-5.6 Terra","Huber quadratic refit",5000,5000,6.82096809237826,8.12272597489504,9.12100942949387,1,,,"unconstrained"
"GPT-5.6 Sol","Huber quadratic refit",5000,5000,8.97215729865538,10.3837005032773,13.0368732413863,1,,,"unconstrained"
"Claude Sonnet 5","Huber quadratic refit",5000,5000,-1.22270759143132,0.021963087190913,1.29240743187527,0.513,,,"unconstrained"
"Claude Opus 5","Huber quadratic refit",5000,5000,-6.29689948017041,0.791483906311011,9.6988174725117,0.555,,,"unconstrained"
"GPT-5.6 Terra","Stochastic frontier",200,200,6.6481508052486,7.42708302513033,8.54846262369815,1,0,0.02,"gamma >= 0"
"GPT-5.6 Terra","Spike + contention",200,200,6.26839639718126,7.67781117669234,8.85029892730253,1,0,0.005,"gamma >= 0"
"GPT-5.6 Sol","Stochastic frontier",200,200,9.34043514946553,10.5685761126606,12.6436210971357,1,0,0.03,"gamma >= 0"
"GPT-5.6 Sol","Spike + contention",200,200,9.31309689265782,10.3200171045314,11.0292063336578,1,0,0.025,"gamma >= 0"
"Claude Sonnet 5","Stochastic frontier",200,200,0,0.010955017031796,0.92810225374885,0.51,0.49,0.49,"gamma >= 0"
"Claude Sonnet 5","Spike + contention",200,200,0,0,1.03368381694656,0.39,0.61,0.65,"gamma >= 0"
"Claude Opus 5","Stochastic frontier",200,200,0,0.755094058900643,8.33216491589698,0.555,0.445,0.455,"gamma >= 0"
"Claude Opus 5","Spike + contention",200,200,0,0.777657609125043,8.24217689007782,0.545,0.455,0.465,"gamma >= 0"
```

### Spike/frontier sigma sensitivity

```csv
"model","estimator","sigma_multiplier","sigma","alpha","beta","gamma","lambda","contention_probability","mean_contention_delay_seconds","log_likelihood","nll","gamma_zero_boundary","any_parameter_boundary"
"GPT-5.6 Terra","Stochastic frontier",0.5,0.114931569648939,0.372910716765701,5.89177714072821,7.31525559386358,2.22021630947765,1,0.450406564320424,-29.0436641446083,29.0436641446083,FALSE,FALSE
"GPT-5.6 Terra","Stochastic frontier",1,0.229863139297879,0.384366816282159,5.78201466854266,7.57935531131049,2.35811534684174,1,0.424067466139566,-35.7098514835679,35.7098514835679,FALSE,FALSE
"GPT-5.6 Terra","Stochastic frontier",2,0.459726278595758,0.406639926246419,5.58934367001216,7.87357803799719,2.4293585211034,1,0.411631297444646,-52.665500402133,52.665500402133,FALSE,FALSE
"GPT-5.6 Terra","Spike + contention",0.5,0.114931569648939,0.506925154884373,6.01784830605027,7.15164903139904,1.52259757161197,0.462555144418017,0.656772359712424,-25.0792248536779,25.0792248536779,FALSE,FALSE
"GPT-5.6 Terra","Spike + contention",1,0.229863139297879,0.621883688810983,5.66875070404015,7.76091475921591,0.790160346305244,0.150541756385702,1.26556591288839,-23.9016240317038,23.9016240317038,FALSE,FALSE
"GPT-5.6 Terra","Spike + contention",2,0.459726278595758,0.6447542075207,5.93746004390064,7.42522964424908,0.553834554824942,0.0764936853497726,1.80559336951463,-42.3594563349459,42.3594563349459,FALSE,FALSE
"GPT-5.6 Sol","Stochastic frontier",0.5,0.165109143066014,0.327172392647103,11.3769654357984,10.6417887455126,2.22156493145704,1,0.450133140760436,-13.0399893848558,13.0399893848558,FALSE,FALSE
"GPT-5.6 Sol","Stochastic frontier",1,0.330218286132028,0.365913941004754,11.403527207433,10.5150312535429,2.34109155681363,1,0.42715117103795,-18.4638023567059,18.4638023567059,FALSE,FALSE
"GPT-5.6 Sol","Stochastic frontier",2,0.660436572264056,0.635060245195124,10.9365596629554,10.7251395552698,3.52807884822316,1,0.283440377332731,-26.7021913523085,26.7021913523085,FALSE,FALSE
"GPT-5.6 Sol","Spike + contention",0.5,0.165109143066014,0.511813778863563,11.1985668070037,10.8752432032688,1.27435868073513,0.360477488715856,0.784708430300908,-9.72982001010198,9.72982001010198,FALSE,FALSE
"GPT-5.6 Sol","Spike + contention",1,0.330218286132028,0.52316968062397,11.8297812873809,10.1697180829468,0.833052925441708,0.154944208236985,1.20040392327987,-14.6739314986812,14.6739314986812,FALSE,FALSE
"GPT-5.6 Sol","Spike + contention",2,0.660436572264056,0.771744668170345,11.0941617074568,10.7010432600049,0.670968588717067,0.0638036223759941,1.49038273447653,-25.125290063681,25.125290063681,FALSE,FALSE
"Claude Sonnet 5","Stochastic frontier",0.5,0.138856199314675,0.29267478320108,12.3107757851853,0.164714062181254,2.0775144257078,1,0.481344431415586,-55.2598281272139,55.2598281272139,FALSE,FALSE
"Claude Sonnet 5","Stochastic frontier",1,0.27771239862935,0.252411271959282,12.7341884080548,0,2.53521226358529,1,0.394444289483597,-62.6650012946589,62.6650012946589,TRUE,TRUE
"Claude Sonnet 5","Stochastic frontier",2,0.5554247972587,0.262359778754978,12.8423980273775,0.17356364499491,3.330997767409,1,0.300210348317899,-84.6843802177408,84.6843802177408,FALSE,FALSE
"Claude Sonnet 5","Spike + contention",0.5,0.138856199314675,0.433961001929887,12.2212063119193,0.196206928599433,1.73740915179092,0.638958024392775,0.575569663006091,-53.2940577279556,53.2940577279556,FALSE,FALSE
"Claude Sonnet 5","Spike + contention",1,0.27771239862935,0.491225140346504,12.6559884862844,0,1.4027190048845,0.261498384934546,0.712901155910654,-57.6600637661387,57.6600637661387,TRUE,TRUE
"Claude Sonnet 5","Spike + contention",2,0.5554247972587,0.513717204235427,12.9610380708666,0,0.284089157240366,0.0124469677080683,3.52002170626282,-73.0741824846283,73.0741824846283,TRUE,TRUE
"Claude Opus 5","Stochastic frontier",0.5,0.64178833039668,0.488073876345565,18.0882499693206,3.54786151577237,0.493136923494675,1,2.0278343647711,-92.5807374808938,92.5807374808938,FALSE,FALSE
"Claude Opus 5","Stochastic frontier",1,1.28357666079336,0.395179025881158,21.0514313669516,0.597781503935594,0.601551011715474,1,1.66236940928459,-97.5192325579967,97.5192325579967,FALSE,FALSE
"Claude Opus 5","Stochastic frontier",2,2.56715332158672,1.85264717761734,21.8096808514548,0,20,1,0.05,-104.129212150925,104.129212150925,TRUE,TRUE
"Claude Opus 5","Spike + contention",0.5,0.64178833039668,1.37534870167398,15.4511464090138,6.38286338736151,0.330777441541631,0.495549254844386,3.02318076873493,-89.3974739844929,89.3974739844929,FALSE,FALSE
"Claude Opus 5","Spike + contention",1,1.28357666079336,1.1172129262983,20.8153611917452,0.778165472677883,0.440393188846358,0.43599990142775,2.27069815184829,-96.638666938007,96.638666938007,FALSE,FALSE
"Claude Opus 5","Spike + contention",2,2.56715332158672,1.90236017065883,21.8096547306953,0,20,0.005,0.05,-104.125794693052,104.125794693052,TRUE,TRUE
```

### Linear-versus-quadratic comparisons

```csv
"model","linear_log_likelihood","quadratic_log_likelihood","two_log_likelihood_improvement","lr_df","lr_p_value","linear_aicc","quadratic_aicc","delta_aicc_linear_minus_quadratic","student_t_gamma","huber_bootstrap_gamma_q025","huber_bootstrap_gamma_median","huber_bootstrap_gamma_q975","huber_bootstrap_fraction_gamma_positive","huber_bootstrap_replicates"
"GPT-5.6 Terra",-74.4547946810192,-35.3063082951718,78.2969727716949,1,8.86576194193947e-19,172.516146739088,97.0126165903436,75.503530148744,8.02646096536283,6.82096809237826,8.12272597489504,9.12100942949387,1,5000
"GPT-5.6 Sol",-38.6183746099002,-18.0909577450025,41.0548337297955,1,1.4801764325651e-10,96.3276583107096,59.0390583471478,37.2885999635618,10.415900440701,8.97215729865538,10.3837005032773,13.0368732413863,1,5000
"Claude Sonnet 5",-61.7758533378969,-61.7070943038001,0.137518068193486,1,0.710760962187429,161.278022465267,163.924826905473,-2.64680444020516,-0.20582264355797,-1.22270759143132,0.021963087190913,1.29240743187527,0.513,5000
"Claude Opus 5",-100.551203194296,-100.477515224352,0.147375939886786,1,0.701055723213336,220.794714080899,223.691872553968,-2.89715847306869,1.57536686814213,-6.29689948017041,0.791483906311011,9.6988174725117,0.555,5000
```

### Extrapolated TTFT values

```csv
"scenario","model","student_t_degree","input_tokens","ttft_seconds","ttft_minutes"
"Primary: quadratic GPT, linear Claude","GPT-5.6 Terra",2,1e+06,14.2199281287846,0.23699880214641
"Primary: quadratic GPT, linear Claude","GPT-5.6 Terra",2,2e+06,43.8418846713271,0.730698077855452
"Primary: quadratic GPT, linear Claude","GPT-5.6 Terra",2,5e+06,229.025285883309,3.81708809805514
"Primary: quadratic GPT, linear Claude","GPT-5.6 Terra",2,1e+07,858.722726517791,14.3120454419632
"Primary: quadratic GPT, linear Claude","GPT-5.6 Sol",2,1e+06,22.5754995444688,0.376258325741147
"Primary: quadratic GPT, linear Claude","GPT-5.6 Sol",2,2e+06,65.388905223806,1.08981508706343
"Primary: quadratic GPT, linear Claude","GPT-5.6 Sol",2,5e+06,318.81992755023,5.3136654591705
"Primary: quadratic GPT, linear Claude","GPT-5.6 Sol",2,1e+07,1157.84098238898,19.297349706483
"Primary: quadratic GPT, linear Claude","Claude Sonnet 5",1,1e+06,13.4265925268349,0.223776542113915
"Primary: quadratic GPT, linear Claude","Claude Sonnet 5",1,2e+06,26.3641773577365,0.439402955962276
"Primary: quadratic GPT, linear Claude","Claude Sonnet 5",1,5e+06,65.1769318504415,1.08628219750736
"Primary: quadratic GPT, linear Claude","Claude Sonnet 5",1,1e+07,129.86485600495,2.16441426674916
"Primary: quadratic GPT, linear Claude","Claude Opus 5",1,1e+06,23.3939672580135,0.389899454300225
"Primary: quadratic GPT, linear Claude","Claude Opus 5",1,2e+06,45.1856838368233,0.753094730613721
"Primary: quadratic GPT, linear Claude","Claude Opus 5",1,5e+06,110.560833573253,1.84268055955421
"Primary: quadratic GPT, linear Claude","Claude Opus 5",1,1e+07,219.519416467301,3.65865694112169
"Opus quadratic sensitivity","Claude Opus 5",2,1e+06,23.732504065855,0.395541734430917
"Opus quadratic sensitivity","Claude Opus 5",2,2e+06,48.8182090055957,0.813636816759928
"Opus quadratic sensitivity","Claude Opus 5",2,5e+06,142.979726242523,2.38299543737539
"Opus quadratic sensitivity","Claude Opus 5",2,1e+07,362.930263029755,6.04883771716258
"Sensitivity: quadratic all models","GPT-5.6 Terra",2,1e+06,14.2199281287846,0.23699880214641
"Sensitivity: quadratic all models","GPT-5.6 Terra",2,2e+06,43.8418846713271,0.730698077855452
"Sensitivity: quadratic all models","GPT-5.6 Terra",2,5e+06,229.025285883309,3.81708809805514
"Sensitivity: quadratic all models","GPT-5.6 Terra",2,1e+07,858.722726517791,14.3120454419632
"Sensitivity: quadratic all models","GPT-5.6 Sol",2,1e+06,22.5754995444688,0.376258325741147
"Sensitivity: quadratic all models","GPT-5.6 Sol",2,2e+06,65.388905223806,1.08981508706343
"Sensitivity: quadratic all models","GPT-5.6 Sol",2,5e+06,318.81992755023,5.3136654591705
"Sensitivity: quadratic all models","GPT-5.6 Sol",2,1e+07,1157.84098238898,19.297349706483
"Sensitivity: quadratic all models","Claude Sonnet 5",2,1e+06,13.3791904928342,0.222986508213903
"Sensitivity: quadratic all models","Claude Sonnet 5",2,2e+06,25.880187087286,0.431336451454767
"Sensitivity: quadratic all models","Claude Sonnet 5",2,5e+06,60.9133051479459,1.01522175246577
"Sensitivity: quadratic all models","Claude Sonnet 5",2,1e+07,111.068929506727,1.85114882511212
"Sensitivity: quadratic all models","Claude Opus 5",2,1e+06,23.732504065855,0.395541734430917
"Sensitivity: quadratic all models","Claude Opus 5",2,2e+06,48.8182090055957,0.813636816759928
"Sensitivity: quadratic all models","Claude Opus 5",2,5e+06,142.979726242523,2.38299543737539
"Sensitivity: quadratic all models","Claude Opus 5",2,1e+07,362.930263029755,6.04883771716258
```

### Marginal latency values

```csv
"model","input_tokens","beta_seconds_per_million_tokens","gamma_seconds_per_million_tokens_squared","derivative_seconds_per_million_tokens","additional_seconds_per_100k_tokens"
"GPT-5.6 Terra",1e+05,5.54257364645402,8.02646096536283,7.14786583952658,0.714786583952658
"GPT-5.6 Terra",272000,5.54257364645402,8.02646096536283,9.9089684116114,0.99089684116114
"GPT-5.6 Terra",5e+05,5.54257364645402,8.02646096536283,13.5690346118168,1.35690346118168
"GPT-5.6 Terra",9e+05,5.54257364645402,8.02646096536283,19.9902033841071,1.99902033841071
"GPT-5.6 Terra",1e+06,5.54257364645402,8.02646096536283,21.5954955771797,2.15954955771797
"GPT-5.6 Terra",2e+06,5.54257364645402,8.02646096536283,37.6484175079053,3.76484175079053
"GPT-5.6 Terra",5e+06,5.54257364645402,8.02646096536283,85.8071833000823,8.58071833000823
"GPT-5.6 Terra",1e+07,5.54257364645402,8.02646096536283,166.071792953711,16.6071792953711
"GPT-5.6 Sol",1e+05,11.5657043572341,10.415900440701,13.6488844453743,1.36488844453743
"GPT-5.6 Sol",272000,11.5657043572341,10.415900440701,17.2319541969755,1.72319541969755
"GPT-5.6 Sol",5e+05,11.5657043572341,10.415900440701,21.9816047979351,2.19816047979351
"GPT-5.6 Sol",9e+05,11.5657043572341,10.415900440701,30.3143251504959,3.03143251504959
"GPT-5.6 Sol",1e+06,11.5657043572341,10.415900440701,32.3975052386361,3.23975052386362
"GPT-5.6 Sol",2e+06,11.5657043572341,10.415900440701,53.2293061200382,5.32293061200382
"GPT-5.6 Sol",5e+06,11.5657043572341,10.415900440701,115.724708764244,11.5724708764244
"GPT-5.6 Sol",1e+07,11.5657043572341,10.415900440701,219.883713171255,21.9883713171255
"Claude Sonnet 5",1e+05,13.1184645251258,-0.20582264355797,13.0772999964142,1.30772999964142
"Claude Sonnet 5",272000,13.1184645251258,-0.20582264355797,13.0064970070302,1.30064970070302
"Claude Sonnet 5",5e+05,13.1184645251258,-0.20582264355797,12.9126418815678,1.29126418815678
"Claude Sonnet 5",9e+05,13.1184645251258,-0.20582264355797,12.7479837667214,1.27479837667214
"Claude Sonnet 5",1e+06,13.1184645251258,-0.20582264355797,12.7068192380098,1.27068192380098
"Claude Sonnet 5",2e+06,13.1184645251258,-0.20582264355797,12.2951739508939,1.22951739508939
"Claude Sonnet 5",5e+06,13.1184645251258,-0.20582264355797,11.0602380895461,1.10602380895461
"Claude Sonnet 5",1e+07,13.1184645251258,-0.20582264355797,9.00201165396636,0.900201165396636
"Claude Opus 5",1e+05,20.3596043353143,1.57536686814213,20.6746777089427,2.06746777089427
"Claude Opus 5",272000,20.3596043353143,1.57536686814213,21.2166039115836,2.12166039115836
"Claude Opus 5",5e+05,20.3596043353143,1.57536686814213,21.9349712034564,2.19349712034564
"Claude Opus 5",9e+05,20.3596043353143,1.57536686814213,23.1952646979701,2.31952646979701
"Claude Opus 5",1e+06,20.3596043353143,1.57536686814213,23.5103380715985,2.35103380715985
"Claude Opus 5",2e+06,20.3596043353143,1.57536686814213,26.6610718078828,2.66610718078828
"Claude Opus 5",5e+06,20.3596043353143,1.57536686814213,36.1132730167356,3.61132730167356
"Claude Opus 5",1e+07,20.3596043353143,1.57536686814213,51.8669416981569,5.18669416981569
```

