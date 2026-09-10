#!/usr/bin/env Rscript
# Offline Astra API supplement. No credentials, provider calls, or other routes.
suppressPackageStartupMessages({library(jsonlite); library(MASS)})
options(digits = 17)
spec <- fromJSON("config/astra_api.json", simplifyVector = FALSE)
output <- "outputs/astra-api"
dir.create(output, recursive = TRUE, showWarnings = FALSE)

read_session <- function(session) {
  records <- lapply(readLines(session$path), fromJSON, simplifyVector = FALSE)
  selected <- Filter(function(r) identical(r$type, "sample") &&
    identical(r$kind, "measured") && isTRUE(r$valid), records)
  stopifnot(length(selected) == session$measured_requests)
  do.call(rbind, lapply(selected, function(r) {
    stopifnot(r$model == "gpt-6-astra", r$provider == "openai")
    data.frame(model = "GPT-6 Astra", session = r$session,
      block = paste0(r$session, ".jsonl:", r$repetition),
      target_tokens = r$target_tokens, total_input_tokens = r$total_input_tokens,
      x = r$total_input_tokens / 1e6, y = r$ttft_ns / 1e9,
      request_started_at = r$request_started_at, request_completed_at = r$request_completed_at,
      new_input_tokens = r$new_input_tokens, cache_read_tokens = r$cache_read_tokens,
      cache_write_tokens = r$cache_write_tokens, output_tokens = r$output_tokens,
      reasoning_tokens = r$reasoning_tokens)
  }))
}
d <- do.call(rbind, lapply(spec$sessions, read_session))
d$block <- factor(d$block)
stopifnot(nrow(d) == 24, nlevels(d$block) == 4)
for (block in levels(d$block)) {
  targets <- d$target_tokens[d$block == block]
  stopifnot(length(targets) == 6, setequal(targets, unlist(spec$nominal_context_tokens)))
}

# Same Student-t specification as the original analysis, with the Astra run's
# tighter optimizer settings. Gamma is unconstrained; df is fixed at four.
fit_student <- function(data, degree) {
  X <- model.matrix(if (degree == 1) ~ x + block else ~ x + I(x^2) + block,
    data, contrasts.arg = list(block = contr.sum(nlevels(data$block))))
  initial <- coef(rlm(x = X, y = data$y, psi = psi.huber, maxit = 200))
  initial_scale <- max(mad(data$y - drop(X %*% initial)), 1e-3)
  objective <- function(parameters) {
    beta <- parameters[seq_len(ncol(X))]
    sigma <- exp(parameters[ncol(X) + 1])
    -sum(dt((data$y - drop(X %*% beta)) / sigma, df = spec$student_t_df,
      log = TRUE) - log(sigma))
  }
  result <- optim(c(initial, log(initial_scale)), objective, method = spec$optimizer$method,
    control = list(maxit = spec$optimizer$maxit, reltol = spec$optimizer$reltol))
  stopifnot(result$convergence == 0)
  beta <- result$par[seq_len(ncol(X))]; names(beta) <- colnames(X)
  k <- ncol(X) + 1; n <- nrow(data)
  list(beta = as.list(beta), sigma = exp(result$par[k]),
    log_likelihood = -result$value, nll = result$value,
    aicc = 2 * result$value + 2 * k + 2 * k * (k + 1) / (n - k - 1),
    degree = degree, df = spec$student_t_df, convergence = result$convergence,
    block_levels = levels(data$block))
}
fits <- list(linear = fit_student(d, 1), quadratic = fit_student(d, 2))
coefficients <- do.call(rbind, lapply(fits, function(f) data.frame(
  model = "GPT-6 Astra", estimator = "Student-t", degree = f$degree,
  alpha = f$beta[["(Intercept)"]], beta = f$beta$x,
  gamma = if (f$degree == 2) f$beta[["I(x^2)"]] else 0,
  sigma = f$sigma, df = f$df, log_likelihood = f$log_likelihood,
  nll = f$nll, aicc = f$aicc, convergence = f$convergence)))
block_effects <- do.call(rbind, lapply(fits, function(f) {
  b <- unlist(f$beta); offsets <- b[grepl("^block", names(b))]
  data.frame(degree = f$degree, block = f$block_levels,
    offset_seconds = c(unname(offsets), -sum(offsets)))
}))
LR <- 2 * (fits$quadratic$log_likelihood - fits$linear$log_likelihood)
comparison <- data.frame(n = nrow(d), blocks = nlevels(d$block), LR = LR,
  LR_p_chisq1 = pchisq(max(LR, 0), 1, lower.tail = FALSE),
  delta_AICc = fits$linear$aicc - fits$quadratic$aicc,
  reference = "asymptotic chi-square(1); model-based, not block-robust")
grid <- seq(min(d$x), max(d$x), length.out = 300)
b <- fits$quadratic$beta
curve <- data.frame(total_input_tokens = grid * 1e6,
  ttft_seconds = b[["(Intercept)"]] + b$x * grid + b[["I(x^2)"]] * grid^2)
write.csv(d, file.path(output, "request_observations.csv"), row.names = FALSE)
write.csv(coefficients, file.path(output, "fit_coefficients.csv"), row.names = FALSE)
write.csv(block_effects, file.path(output, "fit_block_effects.csv"), row.names = FALSE)
write.csv(comparison, file.path(output, "linear_quadratic_comparison.csv"), row.names = FALSE)
write.csv(curve, file.path(output, "quadratic_curve.csv"), row.names = FALSE)
write_json(fits, file.path(output, "student_fits.json"), pretty = TRUE, auto_unbox = TRUE, digits = 16)
print(coefficients, row.names = FALSE)

# Same whole-block Huber procedure as the original four-model analysis.
# This release uses an independent API-only seeded stream, not the incidental
# RNG state left by unrelated exploratory fits. Save every sampled block index.
boot_spec <- spec$huber_bootstrap
huber_fit <- function(data) {
  data$block <- droplevels(factor(data$block))
  rlm(y ~ x + I(x^2) + block, data = data, psi = psi.huber, k = boot_spec$psi_k,
    method = "M", scale.est = "MAD", init = "ls", maxit = boot_spec$maxit,
    acc = 1e-4, test.vec = "resid",
    contrasts = list(block = contr.treatment(nlevels(data$block))))
}
point_fit <- huber_fit(d)
stopifnot(point_fit$converged)
RNGkind(kind = boot_spec$rng_kind[[1]], normal.kind = boot_spec$rng_kind[[2]],
  sample.kind = boot_spec$rng_kind[[3]])
set.seed(boot_spec$seed)
B <- boot_spec$replicates
block_levels <- levels(d$block)
draws <- lapply(seq_len(B), function(i) {
  selected <- sample(seq_along(block_levels), length(block_levels), replace = TRUE)
  pieces <- Map(function(index, copy_index) {
    piece <- d[d$block == block_levels[index], ]
    piece$block <- paste0("boot_", copy_index)
    piece
  }, selected, seq_along(selected))
  sampled <- do.call(rbind, pieces)
  sampled$block <- factor(sampled$block)
  rownames(sampled) <- NULL
  fit <- tryCatch(suppressWarnings(huber_fit(sampled)), error = function(e) NULL)
  data.frame(replicate = i, sampled_block_1 = selected[1],
    sampled_block_2 = selected[2], sampled_block_3 = selected[3], sampled_block_4 = selected[4],
    gamma = if (is.null(fit)) NA_real_ else unname(coef(fit)["I(x^2)"]),
    converged = !is.null(fit) && isTRUE(fit$converged))
})
draws <- do.call(rbind, draws)
good <- draws$converged & is.finite(draws$gamma)
stopifnot(any(good))
tail_probability <- (1 - boot_spec$confidence_level) / 2
ci <- quantile(draws$gamma[good], c(tail_probability, 1 - tail_probability),
  type = boot_spec$quantile_type, names = FALSE)
interval <- data.frame(model = "GPT-6 Astra", estimator = "Huber quadratic",
  parameter = "gamma", estimate = unname(coef(point_fit)["I(x^2)"]),
  ci_low = ci[1], ci_high = ci[2], confidence_level = boot_spec$confidence_level,
  interval = "whole-block pairs bootstrap; percentile type 7",
  fraction_gamma_positive = mean(draws$gamma[good] > 0),
  requested_replicates = B, converged_replicates = sum(good),
  excluded_replicates = sum(!good), blocks = nlevels(d$block),
  seed = boot_spec$seed, psi_k = boot_spec$psi_k,
  note = "fraction positive is not a calibrated p-value; only four observed blocks")
write.csv(draws, file.path(output, "huber_block_bootstrap.csv"), row.names = FALSE)
write.csv(data.frame(block_index = seq_along(block_levels), block = block_levels),
  file.path(output, "bootstrap_block_index.csv"), row.names = FALSE)
write.csv(interval, file.path(output, "bootstrap_intervals.csv"), row.names = FALSE)
print(interval, row.names = FALSE)
