#!/usr/bin/env Rscript

# Generate the authoritative numerical appendix for the four datasets used in
# the finalized publication figures. No exploratory or pooled Claude sessions
# are included.

suppressPackageStartupMessages({
  library(jsonlite)
  library(MASS)
})

options(digits = 17)

dir.create("outputs/tables", recursive = TRUE, showWarnings = FALSE)
dir.create("outputs/bootstrap", recursive = TRUE, showWarnings = FALSE)
output_path <- "docs/results.md"
bootstrap_count_huber <- as.integer(
  Sys.getenv("TTFT_HUBER_BOOTSTRAPS", "5000")
)
bootstrap_count_asymmetric <- as.integer(
  Sys.getenv("TTFT_FINAL_ASYMMETRIC_BOOTSTRAPS", "200")
)

dataset_specs <- list(
  "GPT-5.6 Terra" = list(
    path = "data/raw/final/20260813T155415Z-6998d614.jsonl",
    shape_name = "Terra shared"
  ),
  "GPT-5.6 Sol" = list(
    path = "data/raw/final/20260814T140715Z-bee825d8.jsonl",
    shape_name = "Sol shared"
  ),
  "Claude Sonnet 5" = list(
    path = "data/raw/final/20260814T154718Z-5dc271b9.jsonl",
    shape_name = "Sonnet Aug 14 shared"
  ),
  "Claude Opus 5" = list(
    path = "data/raw/final/20260813T163222Z-b3406d60.jsonl",
    shape_name = "Opus Aug 13 shared"
  )
)

read_final_run <- function(path) {
  session <- fromJSON(readLines(path, n = 1), simplifyVector = TRUE)
  records <- stream_in(file(path), verbose = FALSE)
  keep <- records$type == "sample" & records$kind == "measured"
  if ("valid" %in% names(records)) keep <- keep & records$valid
  records <- records[keep, ]
  data <- data.frame(
    x = records$target_tokens / 1e6,
    y = records$ttft_ns / 1e9,
    target = records$target_tokens,
    total_input_tokens = records$total_input_tokens,
    repetition = records$repetition + 1,
    block = factor(records$repetition + 1)
  )
  list(session = session, data = data)
}

runs <- lapply(dataset_specs, function(specification) {
  read_final_run(specification$path)
})

design_matrix <- function(data, degree, block_levels = levels(data$block)) {
  data$block <- factor(data$block, levels = block_levels)
  rhs <- if (degree == 1) "x + block" else "x + I(x^2) + block"
  model.matrix(
    as.formula(paste("~", rhs)),
    data,
    contrasts.arg = list(block = contr.sum(length(block_levels)))
  )
}

aicc <- function(log_likelihood, parameter_count, observation_count) {
  -2 * log_likelihood + 2 * parameter_count +
    2 * parameter_count * (parameter_count + 1) /
      (observation_count - parameter_count - 1)
}

fit_student_t <- function(data, degree, df = 4) {
  block_levels <- levels(data$block)
  X <- design_matrix(data, degree, block_levels)
  initial_fit <- rlm(x = X, y = data$y, psi = psi.huber, maxit = 200)
  initial <- coef(initial_fit)
  initial_scale <- max(mad(data$y - drop(X %*% initial)), 1e-3)
  objective <- function(parameters) {
    beta <- parameters[seq_len(ncol(X))]
    sigma <- exp(parameters[ncol(X) + 1])
    residual <- (data$y - drop(X %*% beta)) / sigma
    -sum(dt(residual, df = df, log = TRUE) - log(sigma))
  }
  optimized <- optim(
    c(initial, log(initial_scale)),
    objective,
    method = "BFGS",
    control = list(maxit = 2000, reltol = 1e-10)
  )
  beta <- optimized$par[seq_len(ncol(X))]
  names(beta) <- colnames(X)
  sigma <- exp(optimized$par[ncol(X) + 1])
  log_likelihood <- -optimized$value
  list(
    degree = degree,
    df = df,
    beta = beta,
    sigma = sigma,
    log_likelihood = log_likelihood,
    nll = optimized$value,
    aicc = aicc(log_likelihood, ncol(X) + 1, nrow(data)),
    convergence = optimized$convergence,
    block_levels = block_levels
  )
}

block_effect_rows <- function(model_name, estimator, fit) {
  block_count <- length(fit$block_levels)
  if (block_count < 2) return(data.frame())
  explicit <- fit$beta[grep("^block", names(fit$beta))]
  effects <- c(unname(explicit), -sum(explicit))
  data.frame(
    model = model_name,
    estimator = estimator,
    block = fit$block_levels,
    effect_seconds = effects,
    coefficient_status = c(
      rep("explicit sum-contrast coefficient", block_count - 1),
      "implied as negative sum of explicit effects"
    )
  )
}

student_fits <- list()
student_fit_rows <- list()
all_block_rows <- list()

for (model_name in names(runs)) {
  data <- runs[[model_name]]$data
  for (degree in 1:2) {
    fit <- fit_student_t(data, degree)
    key <- paste(model_name, degree, sep = "::")
    student_fits[[key]] <- fit
    student_fit_rows[[length(student_fit_rows) + 1]] <- data.frame(
      model = model_name,
      estimator = "Student-t",
      degree = degree,
      alpha = unname(fit$beta["(Intercept)"]),
      beta = unname(fit$beta["x"]),
      gamma = if (degree == 2) unname(fit$beta["I(x^2)"]) else 0,
      sigma = fit$sigma,
      df = fit$df,
      lambda = NA_real_,
      contention_probability = NA_real_,
      mean_contention_delay_seconds = NA_real_,
      log_likelihood = fit$log_likelihood,
      nll = fit$nll,
      aicc = fit$aicc,
      convergence = fit$convergence,
      gamma_zero_boundary = FALSE,
      any_parameter_boundary = FALSE
    )
    all_block_rows[[length(all_block_rows) + 1]] <- block_effect_rows(
      model_name,
      paste0("Student-t degree ", degree),
      fit
    )
  }
}

student_fit_table <- do.call(rbind, student_fit_rows)

# Asymmetric latency models. The intrinsic slope and curvature are constrained
# nonnegative, and clean sigma is anchored from the lower side of a quadratic
# Huber pilot fit.
log_exgaussian <- function(residual, sigma, rate) {
  z <- residual / sigma - rate * sigma
  log(rate) - rate * residual + 0.5 * (rate * sigma)^2 +
    pnorm(z, log.p = TRUE)
}

log_sum_exp2 <- function(a, b) {
  maximum <- pmax(a, b)
  maximum + log(exp(a - maximum) + exp(b - maximum))
}

parameter_bounds <- function(coefficient_names, family, fixed_sigma) {
  count <- length(coefficient_names)
  lower <- rep(-100, count)
  upper <- rep(100, count)
  names(lower) <- names(upper) <- coefficient_names
  lower["(Intercept)"] <- -50
  upper["(Intercept)"] <- 50
  lower["x"] <- 0
  upper["x"] <- 100
  if ("I(x^2)" %in% coefficient_names) {
    lower["I(x^2)"] <- 0
    upper["I(x^2)"] <- 100
  }
  lower <- c(lower, log_rate = log(0.01))
  upper <- c(upper, log_rate = log(20))
  if (family == "spike_exponential") {
    lower <- c(lower, logit_contended = qlogis(0.005))
    upper <- c(upper, logit_contended = qlogis(0.995))
  }
  list(lower = lower, upper = upper)
}

asymmetric_nll <- function(parameters, X, y, family, fixed_sigma) {
  coefficient_count <- ncol(X)
  beta <- parameters[seq_len(coefficient_count)]
  rate_index <- coefficient_count + 1
  rate <- exp(parameters[rate_index])
  residual <- y - drop(X %*% beta)
  contended <- log_exgaussian(residual, fixed_sigma, rate)
  if (family == "frontier_exponential") return(-sum(contended))
  probability <- plogis(parameters[rate_index + 1])
  clean <- dnorm(residual, sd = fixed_sigma, log = TRUE)
  mixture <- log_sum_exp2(
    log1p(-probability) + clean,
    log(probability) + contended
  )
  -sum(mixture)
}

initial_asymmetric <- function(X, y, family, probability, fixed_sigma) {
  robust <- tryCatch(
    rlm(x = X, y = y, psi = psi.huber, maxit = 200),
    error = function(error) NULL
  )
  beta <- if (is.null(robust)) lm.fit(X, y)$coefficients else coef(robust)
  beta[!is.finite(beta)] <- 0
  beta["x"] <- max(0, beta["x"])
  if ("I(x^2)" %in% names(beta)) {
    beta["I(x^2)"] <- max(0, beta["I(x^2)"])
  }
  residual <- y - drop(X %*% beta)
  positive_mean <- mean(pmax(residual, 0))
  mean_delay <- max(0.1, positive_mean / max(probability, 0.05))
  parameters <- c(beta, log_rate = log(1 / mean_delay))
  if (family == "spike_exponential") {
    parameters <- c(parameters, logit_contended = qlogis(probability))
  }
  parameters
}

estimate_clean_sigma <- function(data) {
  data$block <- droplevels(data$block)
  pilot <- rlm(
    y ~ x + I(x^2) + block,
    data = data,
    psi = psi.huber,
    maxit = 200,
    contrasts = list(block = contr.sum(nlevels(data$block)))
  )
  residual <- residuals(pilot)
  lower_side <- residual[residual <= 0]
  max(0.02, median(abs(lower_side)) / qnorm(0.75))
}

fit_asymmetric <- function(data, family, fixed_sigma) {
  block_levels <- levels(data$block)
  X <- design_matrix(data, 2, block_levels)
  bounds <- parameter_bounds(colnames(X), family, fixed_sigma)
  probabilities <- if (family == "spike_exponential") {
    c(0.1, 0.35, 0.7, 0.9)
  } else {
    0.35
  }
  starts <- lapply(probabilities, function(probability) {
    initial_asymmetric(X, data$y, family, probability, fixed_sigma)
  })
  candidates <- lapply(starts, function(start) {
    start <- pmax(bounds$lower + 1e-8, pmin(bounds$upper - 1e-8, start))
    tryCatch(
      optim(
        start,
        asymmetric_nll,
        X = X,
        y = data$y,
        family = family,
        fixed_sigma = fixed_sigma,
        method = "L-BFGS-B",
        lower = bounds$lower,
        upper = bounds$upper,
        control = list(maxit = 3000, factr = 1e7, pgtol = 1e-8)
      ),
      error = function(error) NULL
    )
  })
  candidates <- Filter(
    function(candidate) !is.null(candidate) && is.finite(candidate$value),
    candidates
  )
  if (!length(candidates)) stop("All asymmetric optimizations failed")
  optimized <- candidates[[which.min(vapply(
    candidates, function(candidate) candidate$value, numeric(1)
  ))]]
  coefficient_count <- ncol(X)
  beta <- optimized$par[seq_len(coefficient_count)]
  names(beta) <- colnames(X)
  rate_index <- coefficient_count + 1
  rate <- exp(optimized$par[rate_index])
  probability <- if (family == "spike_exponential") {
    plogis(optimized$par[rate_index + 1])
  } else {
    1
  }
  tolerance <- 1e-4
  any_boundary <- any(
    abs(optimized$par - bounds$lower) < tolerance |
      abs(optimized$par - bounds$upper) < tolerance
  )
  list(
    family = family,
    degree = 2,
    beta = beta,
    sigma = fixed_sigma,
    rate = rate,
    probability = probability,
    nll = optimized$value,
    log_likelihood = -optimized$value,
    convergence = optimized$convergence,
    gamma_zero_boundary = unname(beta["I(x^2)"]) < 1e-6,
    any_boundary = any_boundary,
    block_levels = block_levels
  )
}

resample_blocks <- function(data) {
  blocks <- levels(data$block)
  selected <- sample(blocks, length(blocks), replace = TRUE)
  pieces <- Map(function(old_block, new_block) {
    piece <- data[data$block == old_block, ]
    piece$block <- paste0("boot_", new_block)
    piece
  }, selected, seq_along(selected))
  sampled <- do.call(rbind, pieces)
  sampled$block <- factor(sampled$block)
  rownames(sampled) <- NULL
  sampled
}

asymmetric_rows <- list()
asymmetric_fits <- list()
sigma_sensitivity_rows <- list()

for (model_name in names(runs)) {
  data <- runs[[model_name]]$data
  sigma_anchor <- estimate_clean_sigma(data)
  for (family in c("frontier_exponential", "spike_exponential")) {
    fit <- fit_asymmetric(data, family, sigma_anchor)
    key <- paste(model_name, family, sep = "::")
    asymmetric_fits[[key]] <- fit
    estimator_name <- if (family == "frontier_exponential") {
      "Stochastic frontier"
    } else {
      "Spike + contention"
    }
    asymmetric_rows[[length(asymmetric_rows) + 1]] <- data.frame(
      model = model_name,
      estimator = estimator_name,
      degree = 2,
      alpha = unname(fit$beta["(Intercept)"]),
      beta = unname(fit$beta["x"]),
      gamma = unname(fit$beta["I(x^2)"]),
      sigma = fit$sigma,
      df = NA_real_,
      lambda = fit$rate,
      contention_probability = fit$probability,
      mean_contention_delay_seconds = 1 / fit$rate,
      log_likelihood = fit$log_likelihood,
      nll = fit$nll,
      aicc = NA_real_,
      convergence = fit$convergence,
      gamma_zero_boundary = fit$gamma_zero_boundary,
      any_parameter_boundary = fit$any_boundary
    )
    all_block_rows[[length(all_block_rows) + 1]] <- block_effect_rows(
      model_name,
      estimator_name,
      fit
    )

    for (multiplier in c(0.5, 1, 2)) {
      sensitivity <- fit_asymmetric(data, family, sigma_anchor * multiplier)
      sigma_sensitivity_rows[[length(sigma_sensitivity_rows) + 1]] <- data.frame(
        model = model_name,
        estimator = estimator_name,
        sigma_multiplier = multiplier,
        sigma = sensitivity$sigma,
        alpha = unname(sensitivity$beta["(Intercept)"]),
        beta = unname(sensitivity$beta["x"]),
        gamma = unname(sensitivity$beta["I(x^2)"]),
        lambda = sensitivity$rate,
        contention_probability = sensitivity$probability,
        mean_contention_delay_seconds = 1 / sensitivity$rate,
        log_likelihood = sensitivity$log_likelihood,
        nll = sensitivity$nll,
        gamma_zero_boundary = sensitivity$gamma_zero_boundary,
        any_parameter_boundary = sensitivity$any_boundary
      )
    }
  }
}

asymmetric_fit_table <- do.call(rbind, asymmetric_rows)
sigma_sensitivity_table <- do.call(rbind, sigma_sensitivity_rows)
fit_coefficient_table <- rbind(student_fit_table, asymmetric_fit_table)
block_effect_table <- do.call(rbind, all_block_rows)

# Final shape evidence: a whole-block bootstrap of quadratic Huber refits.
# This is explicitly distinguished from a Student-t MLE bootstrap.
huber_quadratic <- function(data) {
  data$block <- droplevels(data$block)
  unname(coef(rlm(
    y ~ x + I(x^2) + block,
    data = data,
    psi = psi.huber,
    maxit = 200
  ))["I(x^2)"])
}

set.seed(20260817)
shape_rows <- list()
huber_draw_rows <- list()
for (model_index in seq_along(runs)) {
  model_name <- names(runs)[[model_index]]
  data <- runs[[model_name]]$data
  # Preserve the factor-level ordering of the finalized bootstrap script. The
  # run-prefixed labels sort lexicographically (for example, block 10 follows
  # block 1), which affects the seeded finite bootstrap sample but not any fit.
  data$block <- factor(paste0(
    "run", model_index, "_", as.integer(as.character(data$block))
  ))
  values <- rep(NA_real_, bootstrap_count_huber)
  for (iteration in seq_len(bootstrap_count_huber)) {
    values[iteration] <- tryCatch(
      huber_quadratic(resample_blocks(data)),
      error = function(error) NA_real_
    )
  }
  valid <- is.finite(values)
  interval <- quantile(
    values[valid], c(0.025, 0.5, 0.975),
    na.rm = TRUE, names = FALSE
  )
  shape_rows[[length(shape_rows) + 1]] <- data.frame(
    dataset = dataset_specs[[model_name]]$shape_name,
    huber_block_bootstrap_q025 = interval[1],
    huber_block_bootstrap_median = interval[2],
    huber_block_bootstrap_q975 = interval[3],
    bootstrap_fraction_quadratic_positive = mean(values[valid] > 0),
    bootstrap_requested = bootstrap_count_huber,
    bootstrap_successful = sum(valid)
  )
  huber_draw_rows[[length(huber_draw_rows) + 1]] <- data.frame(
    model = model_name,
    iteration = seq_len(bootstrap_count_huber),
    gamma = values
  )
  cat("Completed Huber bootstrap:", model_name, "\n")
}
shape_evidence <- do.call(rbind, shape_rows)
huber_draw_table <- do.call(rbind, huber_draw_rows)

comparison_rows <- list()
huber_bootstrap_rows <- list()
for (model_name in names(runs)) {
  linear <- student_fits[[paste(model_name, 1, sep = "::")]]
  quadratic <- student_fits[[paste(model_name, 2, sep = "::")]]
  statistic <- 2 * (quadratic$log_likelihood - linear$log_likelihood)
  p_value <- pchisq(max(0, statistic), df = 1, lower.tail = FALSE)
  evidence_name <- dataset_specs[[model_name]]$shape_name
  evidence <- shape_evidence[shape_evidence$dataset == evidence_name, ]
  if (nrow(evidence) != 1) stop("Missing final shape evidence for ", model_name)
  comparison_rows[[length(comparison_rows) + 1]] <- data.frame(
    model = model_name,
    linear_log_likelihood = linear$log_likelihood,
    quadratic_log_likelihood = quadratic$log_likelihood,
    two_log_likelihood_improvement = statistic,
    lr_df = 1,
    lr_p_value = p_value,
    linear_aicc = linear$aicc,
    quadratic_aicc = quadratic$aicc,
    delta_aicc_linear_minus_quadratic = linear$aicc - quadratic$aicc,
    student_t_gamma = unname(quadratic$beta["I(x^2)"]),
    huber_bootstrap_gamma_q025 = evidence$huber_block_bootstrap_q025,
    huber_bootstrap_gamma_median = evidence$huber_block_bootstrap_median,
    huber_bootstrap_gamma_q975 = evidence$huber_block_bootstrap_q975,
    huber_bootstrap_fraction_gamma_positive =
      evidence$bootstrap_fraction_quadratic_positive,
    huber_bootstrap_replicates = bootstrap_count_huber
  )
  huber_bootstrap_rows[[length(huber_bootstrap_rows) + 1]] <- data.frame(
    model = model_name,
    estimator = "Huber quadratic refit",
    requested = evidence$bootstrap_requested,
    successful = evidence$bootstrap_successful,
    gamma_q025 = evidence$huber_block_bootstrap_q025,
    gamma_median = evidence$huber_block_bootstrap_median,
    gamma_q975 = evidence$huber_block_bootstrap_q975,
    fraction_gamma_positive = evidence$bootstrap_fraction_quadratic_positive,
    fraction_gamma_zero = NA_real_,
    fraction_any_parameter_boundary = NA_real_,
    gamma_constraint = "unconstrained"
  )
}
comparison_table <- do.call(rbind, comparison_rows)

# Refit the constrained asymmetric models in whole-block bootstrap samples.
set.seed(20260819)
asymmetric_bootstrap_rows <- list()
asymmetric_draw_rows <- list()
for (model_name in names(runs)) {
  data <- runs[[model_name]]$data
  for (family in c("frontier_exponential", "spike_exponential")) {
    gamma <- rep(NA_real_, bootstrap_count_asymmetric)
    any_boundary <- rep(NA, bootstrap_count_asymmetric)
    for (iteration in seq_len(bootstrap_count_asymmetric)) {
      sampled <- resample_blocks(data)
      candidate <- tryCatch({
        sampled_sigma <- estimate_clean_sigma(sampled)
        fit_asymmetric(sampled, family, sampled_sigma)
      }, error = function(error) NULL)
      if (!is.null(candidate)) {
        gamma[iteration] <- unname(candidate$beta["I(x^2)"])
        any_boundary[iteration] <- candidate$any_boundary
      }
    }
    valid <- is.finite(gamma)
    interval <- quantile(
      gamma[valid], c(0.025, 0.5, 0.975), na.rm = TRUE, names = FALSE
    )
    asymmetric_draw_rows[[length(asymmetric_draw_rows) + 1]] <- data.frame(
      model = model_name,
      estimator = if (family == "frontier_exponential") {
        "Stochastic frontier"
      } else {
        "Spike + contention"
      },
      iteration = seq_len(bootstrap_count_asymmetric),
      gamma = gamma,
      any_parameter_boundary = any_boundary
    )
    asymmetric_bootstrap_rows[[length(asymmetric_bootstrap_rows) + 1]] <- data.frame(
      model = model_name,
      estimator = if (family == "frontier_exponential") {
        "Stochastic frontier"
      } else {
        "Spike + contention"
      },
      requested = bootstrap_count_asymmetric,
      successful = sum(valid),
      gamma_q025 = interval[1],
      gamma_median = interval[2],
      gamma_q975 = interval[3],
      fraction_gamma_positive = mean(gamma[valid] > 1e-6),
      fraction_gamma_zero = mean(gamma[valid] <= 1e-6),
      fraction_any_parameter_boundary = mean(any_boundary[valid]),
      gamma_constraint = "gamma >= 0"
    )
  }
  cat("Completed asymmetric bootstrap:", model_name, "\n")
}

bootstrap_interval_table <- rbind(
  do.call(rbind, huber_bootstrap_rows),
  do.call(rbind, asymmetric_bootstrap_rows)
)
asymmetric_draw_table <- do.call(rbind, asymmetric_draw_rows)

# Dataset metadata.
metadata_rows <- list()
for (model_name in names(runs)) {
  run <- runs[[model_name]]
  session <- run$session
  data <- run$data
  counts <- table(data$target)
  repetitions_description <- if (length(unique(as.integer(counts))) == 1) {
    paste0(unique(as.integer(counts)), " per context length")
  } else {
    paste(paste(names(counts), as.integer(counts), sep = ":"), collapse = "; ")
  }
  metadata_rows[[length(metadata_rows) + 1]] <- data.frame(
    model = model_name,
    session_id = session$session,
    session_label = session$label,
    requests = nrow(data),
    chronological_blocks = nlevels(data$block),
    minimum_total_input_tokens = min(data$total_input_tokens),
    maximum_total_input_tokens = max(data$total_input_tokens),
    target_context_lengths = paste(sort(unique(data$target)), collapse = ";"),
    exact_total_input_lengths = paste(
      sort(unique(data$total_input_tokens)), collapse = ";"
    ),
    repetitions = repetitions_description
  )
}
metadata_table <- do.call(rbind, metadata_rows)

# Extrapolations and marginal latency.
evaluation_millions <- c(1, 2, 5, 10)
primary_degree <- c(
  "GPT-5.6 Terra" = 2,
  "GPT-5.6 Sol" = 2,
  "Claude Sonnet 5" = 1,
  "Claude Opus 5" = 1
)

predict_student <- function(model_name, degree, x) {
  fit <- student_fits[[paste(model_name, degree, sep = "::")]]
  result <- unname(fit$beta["(Intercept)"]) + unname(fit$beta["x"]) * x
  if (degree == 2) result <- result + unname(fit$beta["I(x^2)"]) * x^2
  result
}

extrapolation_rows <- list()
for (model_name in names(runs)) {
  degree <- unname(primary_degree[model_name])
  seconds <- predict_student(model_name, degree, evaluation_millions)
  extrapolation_rows[[length(extrapolation_rows) + 1]] <- data.frame(
    scenario = "Primary: quadratic GPT, linear Claude",
    model = model_name,
    student_t_degree = degree,
    input_tokens = evaluation_millions * 1e6,
    ttft_seconds = seconds,
    ttft_minutes = seconds / 60
  )
}

opus_quadratic_seconds <- predict_student(
  "Claude Opus 5", 2, evaluation_millions
)
extrapolation_rows[[length(extrapolation_rows) + 1]] <- data.frame(
  scenario = "Opus quadratic sensitivity",
  model = "Claude Opus 5",
  student_t_degree = 2,
  input_tokens = evaluation_millions * 1e6,
  ttft_seconds = opus_quadratic_seconds,
  ttft_minutes = opus_quadratic_seconds / 60
)

for (model_name in names(runs)) {
  seconds <- predict_student(model_name, 2, evaluation_millions)
  extrapolation_rows[[length(extrapolation_rows) + 1]] <- data.frame(
    scenario = "Sensitivity: quadratic all models",
    model = model_name,
    student_t_degree = 2,
    input_tokens = evaluation_millions * 1e6,
    ttft_seconds = seconds,
    ttft_minutes = seconds / 60
  )
}
extrapolation_table <- do.call(rbind, extrapolation_rows)

marginal_points_tokens <- c(100000, 272000, 500000, 900000, 1e6, 2e6, 5e6, 10e6)
marginal_rows <- list()
for (model_name in names(runs)) {
  fit <- student_fits[[paste(model_name, 2, sep = "::")]]
  beta <- unname(fit$beta["x"])
  gamma <- unname(fit$beta["I(x^2)"])
  x_million <- marginal_points_tokens / 1e6
  derivative_per_million <- beta + 2 * gamma * x_million
  marginal_rows[[length(marginal_rows) + 1]] <- data.frame(
    model = model_name,
    input_tokens = marginal_points_tokens,
    beta_seconds_per_million_tokens = beta,
    gamma_seconds_per_million_tokens_squared = gamma,
    derivative_seconds_per_million_tokens = derivative_per_million,
    additional_seconds_per_100k_tokens = derivative_per_million / 10
  )
}
marginal_table <- do.call(rbind, marginal_rows)

# Request-level plotting data are exported from the same in-memory datasets used
# for fitting. Figures therefore have no independent coefficient/data source.
plot_rows <- list()
for (model_name in names(runs)) {
  data <- runs[[model_name]]$data
  plot_rows[[length(plot_rows) + 1]] <- data.frame(
    model = model_name,
    target_tokens = data$target,
    total_input_tokens = data$total_input_tokens,
    block = as.integer(as.character(data$block)),
    ttft_seconds = data$y
  )
}
plot_table <- do.call(rbind, plot_rows)

write.csv(
  fit_coefficient_table,
  "outputs/tables/fit_coefficients.csv",
  row.names = FALSE
)
write.csv(
  block_effect_table,
  "outputs/tables/fit_block_effects.csv",
  row.names = FALSE
)
write.csv(
  bootstrap_interval_table,
  "outputs/tables/bootstrap_intervals.csv",
  row.names = FALSE
)
write.csv(
  comparison_table,
  "outputs/tables/linear_quadratic_comparisons.csv",
  row.names = FALSE
)
write.csv(
  extrapolation_table,
  "outputs/tables/extrapolated_ttft.csv",
  row.names = FALSE
)
write.csv(
  marginal_table,
  "outputs/tables/marginal_latency.csv",
  row.names = FALSE
)
write.csv(
  sigma_sensitivity_table,
  "outputs/tables/asymmetric_sigma_sensitivity.csv",
  row.names = FALSE
)
write.csv(
  metadata_table,
  "outputs/tables/session_metadata.csv",
  row.names = FALSE
)
write.csv(
  plot_table,
  "outputs/tables/request_observations.csv",
  row.names = FALSE
)
write.csv(
  huber_draw_table,
  "outputs/bootstrap/huber_block_bootstrap.csv",
  row.names = FALSE
)
write.csv(
  asymmetric_draw_table,
  "outputs/bootstrap/asymmetric_block_bootstrap.csv",
  row.names = FALSE
)

format_number <- function(value, digits = 12) {
  if (is.na(value)) return("NA")
  format(value, digits = digits, scientific = FALSE, trim = TRUE)
}

markdown_table <- function(data, digits = 10) {
  formatted <- data
  for (column in names(formatted)) {
    if (is.numeric(formatted[[column]])) {
      formatted[[column]] <- vapply(
        formatted[[column]], format_number, character(1), digits = digits
      )
    }
  }
  header <- paste0("| ", paste(names(formatted), collapse = " | "), " |")
  separator <- paste0("| ", paste(rep("---", ncol(formatted)), collapse = " | "), " |")
  rows <- apply(formatted, 1, function(row) {
    paste0("| ", paste(row, collapse = " | "), " |")
  })
  paste(c(header, separator, rows), collapse = "\n")
}

csv_block <- function(data) {
  lines <- capture.output(write.csv(data, row.names = FALSE, na = ""))
  paste(c("```csv", lines, "```"), collapse = "\n")
}

lines <- c(
  "# Final authoritative TTFT results",
  "",
  paste0(
    "Generated from the exact four sessions used in the finalized publication ",
    "figures. Claude sessions are not pooled across days. `x` is measured in ",
    "millions of target input tokens, and TTFT is measured in seconds."
  ),
  "",
  "## 1. Dataset metadata",
  "",
  markdown_table(metadata_table),
  "",
  paste0(
    "All four sessions used a shared approximately 2,048-token cached prefix; ",
    "the rest of each measured prompt was new input. Requests were sequential ",
    "and each chronological block contained one request at every tested length."
  ),
  "",
  "## 2. Student-t linear fits",
  "",
  markdown_table(student_fit_table[student_fit_table$degree == 1, c(
    "model", "alpha", "beta", "sigma", "df", "log_likelihood", "nll", "aicc"
  )]),
  "",
  paste0(
    "The complete sum-to-zero block effects are reported in the machine-readable ",
    "block-effect table at the end."
  ),
  "",
  "## 3. Student-t quadratic fits",
  "",
  markdown_table(student_fit_table[student_fit_table$degree == 2, c(
    "model", "alpha", "beta", "gamma", "sigma", "df",
    "log_likelihood", "nll", "aicc"
  )]),
  "",
  paste0(
    "The finalized uncertainty interval for curvature is a 5,000-replicate ",
    "whole-block bootstrap of a quadratic Huber refit. A separate Student-t MLE ",
    "bootstrap was not part of the finalized analysis and is therefore not ",
    "substituted here."
  ),
  "",
  markdown_table(comparison_table[, c(
    "model", "two_log_likelihood_improvement", "lr_p_value",
    "huber_bootstrap_gamma_q025", "huber_bootstrap_gamma_median",
    "huber_bootstrap_gamma_q975", "huber_bootstrap_fraction_gamma_positive"
  )]),
  "",
  "## 4. Stochastic-frontier quadratic fits",
  "",
  markdown_table(asymmetric_fit_table[
    asymmetric_fit_table$estimator == "Stochastic frontier",
    c("model", "alpha", "beta", "gamma", "sigma", "lambda",
      "mean_contention_delay_seconds", "log_likelihood", "nll",
      "gamma_zero_boundary", "any_parameter_boundary")
  ]),
  "",
  paste0(
    "For the frontier model, every request has an exponential nonnegative delay, ",
    "so the implied contention probability is 1 and the mean delay is `1/lambda`."
  ),
  "",
  "## 5. Spike-plus-contention quadratic fits",
  "",
  markdown_table(asymmetric_fit_table[
    asymmetric_fit_table$estimator == "Spike + contention",
    c("model", "alpha", "beta", "gamma", "sigma", "lambda",
      "contention_probability", "mean_contention_delay_seconds",
      "log_likelihood", "nll", "gamma_zero_boundary", "any_parameter_boundary")
  ]),
  "",
  paste0(
    "`contention_probability` is pi. The mean delay conditional on contention is ",
    "`1/lambda`. Sigma was anchored rather than estimated freely. The 0.5x and ",
    "2x sigma sensitivity fits, including gamma, appear below."
  ),
  "",
  markdown_table(sigma_sensitivity_table[
    sigma_sensitivity_table$estimator == "Spike + contention",
  ]),
  "",
  "### Asymmetric-model curvature bootstrap",
  "",
  markdown_table(bootstrap_interval_table[
    bootstrap_interval_table$estimator != "Huber quadratic refit",
  ]),
  "",
  "## 6. Linear-versus-quadratic conclusion",
  "",
  markdown_table(comparison_table[, c(
    "model", "two_log_likelihood_improvement", "lr_p_value",
    "delta_aicc_linear_minus_quadratic", "student_t_gamma",
    "huber_bootstrap_gamma_q025", "huber_bootstrap_gamma_q975",
    "huber_bootstrap_fraction_gamma_positive"
  )]),
  "",
  paste0(
    "Numerically: Terra and Sol have large positive likelihood improvements and ",
    "5,000/5,000 positive Huber-bootstrap curvature estimates. Sonnet and Opus ",
    "have likelihood-ratio p-values near 0.71 and 0.70 respectively, negative ",
    "AICc improvements, bootstrap intervals spanning zero, and positive-curvature ",
    "fractions near one half. This states only the statistical comparison."
  ),
  "",
  "## 7. Extrapolation values",
  "",
  paste0(
    "The primary scenario uses quadratic Student-t fits for Terra and Sol and ",
    "linear Student-t fits for Sonnet and Opus. Values beyond the approximately ",
    "0.9M measured range are illustrative extrapolations, not empirical API ",
    "latency measurements."
  ),
  "",
  markdown_table(extrapolation_table[
    extrapolation_table$scenario == "Primary: quadratic GPT, linear Claude",
  ]),
  "",
  "### Opus quadratic Student-t sensitivity",
  "",
  markdown_table(extrapolation_table[
    extrapolation_table$scenario == "Opus quadratic sensitivity",
  ]),
  "",
  "### All-four-quadratic Student-t sensitivity",
  "",
  markdown_table(extrapolation_table[
    extrapolation_table$scenario == "Sensitivity: quadratic all models",
  ]),
  "",
  "## 8. Marginal latency from every quadratic Student-t fit",
  "",
  paste0(
    "For `x` in millions of tokens, `dTTFT/dx = beta + 2*gamma*x` gives ",
    "seconds per additional million tokens. The final column divides this by ",
    "10 to report seconds of additional TTFT per additional 100k tokens."
  ),
  "",
  markdown_table(marginal_table),
  "",
  "## 9. Exact fitting conventions",
  "",
  "- `x = target_tokens / 1e6`; alpha is seconds, beta is seconds per million tokens, and gamma is seconds per million tokens squared.",
  "- Student-t residual degrees of freedom were fixed at 4. Alpha, beta, gamma, and block effects were unconstrained; sigma was positive through a log-sigma parameterization.",
  "- Student-t fits used maximum likelihood via R `optim(method = \"BFGS\", maxit = 2000, reltol = 1e-10)`, initialized from `MASS::rlm` with Huber loss and a MAD residual scale.",
  "- Chronological block effects used `contr.sum(K)`: K-1 explicit coefficients plus a final effect equal to the negative sum, making the reported alpha the average-block intercept.",
  "- The finalized general curvature interval resampled whole chronological blocks with replacement and refitted quadratic Huber regression 5,000 times (`set.seed(20260817)`). Requests within a selected block stayed together.",
  paste0(
    "- The frontier and spike curvature intervals below used the same whole-block ",
    "resampling logic for ", bootstrap_count_asymmetric,
    " replicates (`set.seed(20260819)`), re-estimating the sigma anchor in every replicate."
  ),
  "- For frontier and spike fits, beta and gamma were constrained to [0, 100], alpha to [-50, 50], block coefficients to [-100, 100], lambda to [0.01, 20], and spike pi to [0.005, 0.995].",
  "- The clean-sigma anchor was `max(0.02, median(abs(r[r <= 0])) / qnorm(0.75))`, where `r` came from a quadratic Huber fit with sum-coded block effects. This is a fixed anchor, not a likelihood penalty. Sensitivities used 0.5 and 2 times this anchor.",
  "- Frontier/spike optimization used R `optim(method = \"L-BFGS-B\", maxit = 3000, factr = 1e7, pgtol = 1e-8)`. Spike fits used starts at pi = 0.1, 0.35, 0.7, and 0.9 and retained the lowest NLL.",
  "- Student-t linear-versus-quadratic LR statistics used one additional unconstrained gamma parameter and a chi-square(1) reference distribution.",
  "",
  "## Machine-readable tables",
  "",
  "### Dataset metadata",
  "",
  csv_block(metadata_table),
  "",
  "### All fit coefficients",
  "",
  csv_block(fit_coefficient_table),
  "",
  "### Block-effect coefficients",
  "",
  csv_block(block_effect_table),
  "",
  "### Bootstrap intervals",
  "",
  csv_block(bootstrap_interval_table),
  "",
  "### Spike/frontier sigma sensitivity",
  "",
  csv_block(sigma_sensitivity_table),
  "",
  "### Linear-versus-quadratic comparisons",
  "",
  csv_block(comparison_table),
  "",
  "### Extrapolated TTFT values",
  "",
  csv_block(extrapolation_table),
  "",
  "### Marginal latency values",
  "",
  csv_block(marginal_table),
  ""
)

writeLines(lines, output_path, useBytes = TRUE)
cat("Wrote", output_path, "\n")
