#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(jsonlite))

read_measurements <- function(path) {
  records <- stream_in(file(path), verbose = FALSE)
  records[records$type == "sample" & records$kind == "measured", ]
}

uncached <- rbind(
  read_measurements("data/raw/supporting/20260812T191605Z-bae8e752.jsonl"),
  read_measurements("data/raw/supporting/20260812T192643Z-50c12a81.jsonl")
)
shared <- read_measurements(
  "data/raw/final/20260814T154718Z-5dc271b9.jsonl"
)

unscaled_mad <- function(values) median(abs(values - median(values)))
rows <- list()
for (target in c(100000, 250000)) {
  for (name in c("uncached", "shared_prefix")) {
    source <- if (name == "uncached") uncached else shared
    values <- source$ttft_ns[source$target_tokens == target] / 1e9
    rows[[length(rows) + 1]] <- data.frame(
      target_tokens = target,
      protocol = name,
      observations = length(values),
      minimum_seconds = min(values),
      median_seconds = median(values),
      maximum_seconds = max(values),
      unscaled_mad_seconds = unscaled_mad(values),
      iqr_seconds = IQR(values)
    )
  }
}

result <- do.call(rbind, rows)
write.csv(result, "outputs/tables/sonnet_dispersion_comparison.csv", row.names = FALSE)
print(result, row.names = FALSE, digits = 6)
