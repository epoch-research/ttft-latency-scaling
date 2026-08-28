#!/usr/bin/env Rscript

# Portable Epoch-styled static exports of the finalized TTFT figures.
#
# This deliberately preserves the fitted coefficients, request-level observations,
# panel scales, and extrapolation forms from the source analysis. Only presentation
# is changed to follow the visual language of Epoch Data Insight exports.

suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
script_arg <- commandArgs(trailingOnly = FALSE)
script_flag <- grep("^--file=", script_arg, value = TRUE)
script_path <- if (length(script_flag)) {
  normalizePath(sub("^--file=", "", script_flag[[1]]))
} else {
  normalizePath("analysis/figures.R")
}
script_dir <- dirname(script_path)
repo_root <- normalizePath(file.path(script_dir, ".."))

output_dir <- if (length(args)) {
  normalizePath(args[[1]], mustWork = FALSE)
} else {
  normalizePath(file.path(repo_root, "figures/reproduced"), mustWork = FALSE)
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# Make the site's bundled Messina fonts available to Cairo without installing
# them globally on the workstation.
font_dir <- normalizePath(file.path(repo_root, "assets/fonts/Inter"))
font_config <- tempfile(fileext = ".conf")
font_cache <- tempfile(pattern = "fontconfig-cache-")
dir.create(font_cache)
writeLines(c(
  "<?xml version=\"1.0\"?>",
  "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">",
  "<fontconfig>",
  "  <include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include>",
  sprintf("  <dir>%s</dir>", font_dir),
  sprintf("  <cachedir>%s</cachedir>", font_cache),
  "</fontconfig>"
), font_config)
Sys.setenv(FONTCONFIG_FILE = font_config)
on.exit(unlink(c(font_config, font_cache), recursive = TRUE), add = TRUE)

font_family <- "Inter"

points <- read.csv(
  file.path(repo_root, "outputs/tables/request_observations.csv"),
  check.names = FALSE
)
all_fits <- read.csv(
  file.path(repo_root, "outputs/tables/fit_coefficients.csv"),
  check.names = FALSE
)
points$model_label <- points$model
to_figure_fits <- function(data) {
  data.frame(
    dataset = data$model,
    method = ifelse(
      data$estimator == "Stochastic frontier",
      "Frontier",
      data$estimator
    ),
    degree = data$degree,
    intercept = data$alpha,
    linear = data$beta,
    quadratic = data$gamma
  )
}
quadratic_fits <- to_figure_fits(all_fits[all_fits$degree == 2, ])
linear_fits <- to_figure_fits(
  all_fits[all_fits$degree == 1 & all_fits$estimator == "Student-t", ]
)

model_order <- c(
  "GPT-5.6 Terra",
  "GPT-5.6 Sol",
  "Claude Sonnet 5",
  "Claude Opus 5"
)
dataset_map <- c(
  "GPT-5.6 Terra" = "GPT-5.6 Terra",
  "GPT-5.6 Sol" = "GPT-5.6 Sol",
  "Claude Sonnet 5" = "Claude Sonnet 5",
  "Claude Opus 5" = "Claude Opus 5"
)

points <- points[points$model_label %in% model_order, ]
points$model_label <- factor(points$model_label, levels = model_order)

prepare_fits <- function(data) {
  data$model_label <- unname(dataset_map[data$dataset])
  data <- data[data$model_label %in% model_order, ]
  data$model_label <- factor(data$model_label, levels = model_order)
  data
}

quadratic_fits <- prepare_fits(quadratic_fits)
linear_fits <- prepare_fits(linear_fits)

# Epoch design tokens, mirrored from legacy/common/colors.ts.
charcoal_1000 <- "#090C0C"
charcoal_900 <- "#212A2A"
charcoal_700 <- "#536565"
charcoal_500 <- "#8B9999"
charcoal_300 <- "#C7CACA"
gray_500 <- "#5C737B"
gray_400 <- "#90A5AB"
gray_300 <- "#CCD8D9"
gray_200 <- "#E2EEEE"
teal <- "#00A5A6"
pink <- "#E03D90"
orange <- "#FC6538"
purple <- "#6A3ECB"

raw_color <- gray_500
single_fit_color <- pink
estimator_colors <- c(
  "Student-t" = teal,
  "Frontier" = pink,
  "Spike + contention" = orange
)
estimator_linetypes <- c(
  "Student-t" = "solid",
  "Frontier" = "dashed",
  "Spike + contention" = "dotted"
)
model_colors <- c(
  "GPT-5.6 Terra" = pink,
  "GPT-5.6 Sol" = orange,
  "Claude Sonnet 5" = teal,
  "Claude Opus 5" = purple
)

curve_rows <- function(fits, methods = unique(fits$method)) {
  rows <- list()
  for (model_name in model_order) {
    model_points <- points[points$model_label == model_name, ]
    grid_millions <- seq(
      min(model_points$total_input_tokens) / 1e6,
      max(model_points$total_input_tokens) / 1e6,
      length.out = 300
    )
    for (method_name in methods) {
      coefficient <- fits[
        fits$model_label == model_name & fits$method == method_name,
      ]
      if (nrow(coefficient) != 1) {
        stop(sprintf("Expected one %s fit for %s", method_name, model_name))
      }
      rows[[length(rows) + 1]] <- data.frame(
        model_label = model_name,
        method = method_name,
        x_thousands = grid_millions * 1000,
        ttft_seconds = coefficient$intercept +
          coefficient$linear * grid_millions +
          coefficient$quadratic * grid_millions^2
      )
    }
  }
  result <- do.call(rbind, rows)
  result$model_label <- factor(result$model_label, levels = model_order)
  result$method <- factor(
    result$method,
    levels = c("Student-t", "Frontier", "Spike + contention")
  )
  result
}

student_curves <- curve_rows(quadratic_fits, "Student-t")
all_estimator_curves <- curve_rows(
  quadratic_fits,
  c("Student-t", "Frontier", "Spike + contention")
)

epoch_theme <- function(show_x_title = TRUE, show_y_title = TRUE,
                        show_x_ticks = TRUE, show_y_ticks = TRUE) {
  theme_classic(base_size = 12, base_family = font_family) +
    theme(
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      panel.grid.major = element_line(color = gray_200, linewidth = 0.45),
      panel.grid.minor = element_blank(),
      axis.line = element_line(color = gray_400, linewidth = 0.45),
      axis.ticks = element_line(color = gray_400, linewidth = 0.45),
      axis.ticks.length = unit(3.5, "pt"),
      axis.text = element_text(size = 10.5, color = charcoal_700),
      axis.text.x = if (show_x_ticks) element_text() else element_blank(),
      axis.text.y = if (show_y_ticks) element_text() else element_blank(),
      axis.ticks.x = if (show_x_ticks) element_line() else element_blank(),
      axis.ticks.y = if (show_y_ticks) element_line() else element_blank(),
      axis.title.x = if (show_x_title) {
        element_text(
          size = 11.5, face = "bold", color = charcoal_1000,
          margin = margin(t = 9, unit = "pt")
        )
      } else {
        element_blank()
      },
      axis.title.y = if (show_y_title) {
        element_text(
          size = 11.5, face = "bold", color = charcoal_1000,
          margin = margin(r = 9, unit = "pt")
        )
      } else {
        element_blank()
      },
      plot.title = element_text(
        size = 14, face = "bold", color = charcoal_1000,
        hjust = 0, margin = margin(b = 8, unit = "pt")
      ),
      legend.position = "none",
      plot.margin = margin(3, 8, 3, 3, unit = "pt")
    )
}

make_panel <- function(model_name, curves, y_limits, y_breaks,
                       show_x_title, show_y_title,
                       show_x_ticks = TRUE, show_y_ticks = TRUE,
                       single_fit = FALSE) {
  model_points <- points[points$model_label == model_name, ]
  model_curves <- curves[curves$model_label == model_name, ]

  panel <- ggplot() +
    geom_point(
      data = model_points,
      aes(x = total_input_tokens / 1000, y = ttft_seconds),
      color = scales::alpha(raw_color, 0.42),
      shape = 16,
      size = 2.7,
      stroke = 0,
      inherit.aes = FALSE
    )

  if (single_fit) {
    panel <- panel + geom_line(
      data = model_curves,
      aes(x = x_thousands, y = ttft_seconds),
      color = single_fit_color,
      linewidth = 1.15,
      lineend = "round",
      inherit.aes = FALSE
    )
  } else {
    panel <- panel +
      geom_line(
        data = model_curves,
        aes(x = x_thousands, y = ttft_seconds, color = method, linetype = method),
        linewidth = 1.05,
        lineend = "round",
        inherit.aes = FALSE
      ) +
      scale_color_manual(values = estimator_colors, drop = FALSE) +
      scale_linetype_manual(values = estimator_linetypes, drop = FALSE)
  }

  panel +
    scale_x_continuous(
      limits = c(0, 950),
      breaks = c(0, 300, 600, 900),
      labels = c("0", "300", "600", "900"),
      expand = expansion(mult = 0)
    ) +
    scale_y_continuous(
      limits = y_limits,
      breaks = y_breaks,
      expand = expansion(mult = 0)
    ) +
    labs(
      title = model_name,
      x = "Input context (thousand tokens)",
      y = "Time to first token (s)"
    ) +
    epoch_theme(show_x_title, show_y_title, show_x_ticks, show_y_ticks)
}

draw_epoch_header <- function(title, subtitle) {
  grid.text(
    title,
    x = unit(0.055, "npc"), y = unit(0.955, "npc"),
    just = c("left", "top"),
    gp = gpar(
      fontfamily = font_family, fontface = "bold", fontsize = 23,
      col = charcoal_1000
    )
  )
  grid.text(
    subtitle,
    x = unit(0.055, "npc"), y = unit(0.895, "npc"),
    just = c("left", "top"),
    gp = gpar(fontfamily = font_family, fontsize = 14, col = charcoal_700)
  )
}

draw_epoch_footer <- function() {
  icon_x <- 0.056
  icon_y <- 0.040
  icon_col <- gray_400
  grid.lines(
    x = unit(c(icon_x, icon_x + 0.019), "npc"),
    y = unit(c(icon_y - 0.006, icon_y + 0.006), "npc"),
    gp = gpar(col = icon_col, lwd = 3.4, lineend = "round")
  )
  grid.lines(
    x = unit(c(icon_x, icon_x + 0.026), "npc"),
    y = unit(c(icon_y + 0.002, icon_y + 0.018), "npc"),
    gp = gpar(col = icon_col, lwd = 3.4, lineend = "round")
  )
  grid.lines(
    x = unit(c(icon_x, icon_x + 0.010), "npc"),
    y = unit(c(icon_y + 0.015, icon_y + 0.021), "npc"),
    gp = gpar(col = icon_col, lwd = 3.4, lineend = "round")
  )
  grid.text(
    "EPOCH AI  |  CC-BY",
    x = unit(0.088, "npc"), y = unit(icon_y + 0.006, "npc"),
    just = c("left", "center"),
    gp = gpar(
      fontfamily = font_family, fontface = "bold", fontsize = 11,
      col = gray_400
    )
  )
  grid.text(
    "epoch.ai",
    x = unit(0.955, "npc"), y = unit(icon_y + 0.006, "npc"),
    just = c("right", "center"),
    gp = gpar(fontfamily = font_family, fontsize = 11, col = gray_500)
  )
}

draw_shared_legend <- function(labels, colors, linetypes, point_flags,
                               y = 0.105, fontsize = 10.8) {
  handle_width <- 0.025
  text_gap <- 0.009
  column_gap <- 0.035
  approximate_text_width <- nchar(labels) * 0.0062
  entry_width <- handle_width + text_gap + approximate_text_width
  total_width <- sum(entry_width) + column_gap * (length(labels) - 1)
  cursor <- (1 - total_width) / 2

  for (index in seq_along(labels)) {
    center <- cursor + handle_width / 2
    if (point_flags[[index]]) {
      grid.points(
        x = unit(center, "npc"), y = unit(y, "npc"),
        pch = 16, size = unit(5.5, "pt"),
        gp = gpar(col = scales::alpha(colors[[index]], 0.55))
      )
    } else {
      line_type <- switch(
        linetypes[[index]],
        solid = 1, dashed = 2, dotted = 3, 1
      )
      grid.lines(
        x = unit(c(cursor, cursor + handle_width), "npc"),
        y = unit(c(y, y), "npc"),
        gp = gpar(
          col = colors[[index]], lty = line_type, lwd = 2.6,
          lineend = "round"
        )
      )
    }
    grid.text(
      labels[[index]],
      x = unit(cursor + handle_width + text_gap, "npc"), y = unit(y, "npc"),
      just = c("left", "center"),
      gp = gpar(fontfamily = font_family, fontsize = fontsize, col = charcoal_900)
    )
    cursor <- cursor + entry_width[[index]] + column_gap
  }
}

draw_panels <- function(panel_list, nrow, ncol, bounds, wspace, hspace = 0.08) {
  panel_width <- (bounds$right - bounds$left) /
    (ncol + (ncol - 1) * wspace)
  panel_height <- (bounds$top - bounds$bottom) /
    (nrow + (nrow - 1) * hspace)
  panel_index <- 1
  for (row in seq_len(nrow)) {
    for (column in seq_len(ncol)) {
      x_left <- bounds$left + (column - 1) * panel_width * (1 + wspace)
      y_bottom <- bounds$bottom + (nrow - row) * panel_height * (1 + hspace)
      print(
        panel_list[[panel_index]],
        vp = viewport(
          x = unit(x_left, "npc"), y = unit(y_bottom, "npc"),
          width = unit(panel_width, "npc"), height = unit(panel_height, "npc"),
          just = c("left", "bottom")
        )
      )
      panel_index <- panel_index + 1
    }
  }
}

export_figure <- function(stem, width, height, draw) {
  path_for <- function(ext) file.path(output_dir, paste0(stem, ".", ext))

  png(
    filename = path_for("png"), width = width, height = height,
    units = "in", res = 240, bg = "white", type = "cairo"
  )
  draw()
  dev.off()

  svg(
    filename = path_for("svg"), width = width, height = height,
    bg = "white", pointsize = 12, family = font_family
  )
  draw()
  dev.off()

  cairo_pdf(
    filename = path_for("pdf"), width = width, height = height,
    bg = "white", family = font_family
  )
  draw()
  dev.off()
}

# Figure 1: common quadratic-capable Student-t fit.
figure_1_panels <- list(
  make_panel(
    "GPT-5.6 Terra", student_curves, c(0, 30), c(0, 10, 20, 30),
    show_x_title = FALSE, show_y_title = TRUE,
    show_x_ticks = FALSE, show_y_ticks = TRUE, single_fit = TRUE
  ),
  make_panel(
    "GPT-5.6 Sol", student_curves, c(0, 30), c(0, 10, 20, 30),
    show_x_title = FALSE, show_y_title = FALSE,
    show_x_ticks = FALSE, show_y_ticks = FALSE, single_fit = TRUE
  ),
  make_panel(
    "Claude Sonnet 5", student_curves, c(0, 30), c(0, 10, 20, 30),
    show_x_title = TRUE, show_y_title = TRUE,
    show_x_ticks = TRUE, show_y_ticks = TRUE, single_fit = TRUE
  ),
  make_panel(
    "Claude Opus 5", student_curves, c(0, 30), c(0, 10, 20, 30),
    show_x_title = TRUE, show_y_title = FALSE,
    show_x_ticks = TRUE, show_y_ticks = FALSE, single_fit = TRUE
  )
)

export_figure("figure_1_headline_four_model_comparison", 12.2, 9.2, function() {
  grid.newpage()
  draw_epoch_header(
    "Time to first token across four frontier language models",
    "Quadratic-capable Student-t fits to shared-prefix requests; each dot is one API request"
  )
  draw_panels(
    figure_1_panels, 2, 2,
    list(left = 0.072, right = 0.965, top = 0.825, bottom = 0.155),
    wspace = 0.14, hspace = 0.20
  )
  draw_shared_legend(
    c("Raw request", "Student-t fit"),
    c(raw_color, single_fit_color),
    c("solid", "solid"),
    c(TRUE, FALSE),
    y = 0.105
  )
  draw_epoch_footer()
})

# Figure 2: GPT estimator robustness.
figure_2_panels <- list(
  make_panel(
    "GPT-5.6 Terra", all_estimator_curves, c(0, 21), c(0, 5, 10, 15, 20),
    show_x_title = TRUE, show_y_title = TRUE,
    show_x_ticks = TRUE, show_y_ticks = TRUE
  ),
  make_panel(
    "GPT-5.6 Sol", all_estimator_curves, c(0, 21), c(0, 5, 10, 15, 20),
    show_x_title = TRUE, show_y_title = FALSE,
    show_x_ticks = TRUE, show_y_ticks = FALSE
  )
)

export_figure("figure_2_gpt_estimator_robustness", 11.7, 6.3, function() {
  grid.newpage()
  draw_epoch_header(
    "GPT-5.6 latency scaling is robust across estimators",
    "Quadratic-capable fits using three treatments of request-level latency noise"
  )
  draw_panels(
    figure_2_panels, 1, 2,
    list(left = 0.078, right = 0.965, top = 0.785, bottom = 0.205),
    wspace = 0.15, hspace = 0
  )
  draw_shared_legend(
    c("Raw request", "Student-t", "Frontier", "Spike + contention"),
    c(raw_color, unname(estimator_colors)),
    c("solid", unname(estimator_linetypes)),
    c(TRUE, FALSE, FALSE, FALSE),
    y = 0.135,
    fontsize = 10.2
  )
  draw_epoch_footer()
})

# Figure 3: Claude estimator robustness.
figure_3_panels <- list(
  make_panel(
    "Claude Sonnet 5", all_estimator_curves, c(0, 30), c(0, 5, 10, 15, 20, 25, 30),
    show_x_title = TRUE, show_y_title = TRUE,
    show_x_ticks = TRUE, show_y_ticks = TRUE
  ),
  make_panel(
    "Claude Opus 5", all_estimator_curves, c(0, 30), c(0, 5, 10, 15, 20, 25, 30),
    show_x_title = TRUE, show_y_title = FALSE,
    show_x_ticks = TRUE, show_y_ticks = FALSE
  )
)

export_figure("figure_3_claude_estimator_robustness", 11.7, 6.3, function() {
  grid.newpage()
  draw_epoch_header(
    "Claude latency scaling across estimators",
    "Quadratic-capable fits using three treatments of request-level latency noise"
  )
  draw_panels(
    figure_3_panels, 1, 2,
    list(left = 0.078, right = 0.965, top = 0.785, bottom = 0.205),
    wspace = 0.15, hspace = 0
  )
  draw_shared_legend(
    c("Raw request", "Student-t", "Frontier", "Spike + contention"),
    c(raw_color, unname(estimator_colors)),
    c("solid", unname(estimator_linetypes)),
    c(TRUE, FALSE, FALSE, FALSE),
    y = 0.135,
    fontsize = 10.2
  )
  draw_epoch_footer()
})

# Figure 4: illustrative extrapolation, quadratic GPT and linear Claude.
student_quadratic <- quadratic_fits[quadratic_fits$method == "Student-t", ]
student_linear <- linear_fits[linear_fits$method == "Student-t", ]
primary_forms <- c(
  "GPT-5.6 Terra" = "quadratic",
  "GPT-5.6 Sol" = "quadratic",
  "Claude Sonnet 5" = "linear",
  "Claude Opus 5" = "linear"
)

extrapolation_rows <- list()
for (model_name in model_order) {
  form <- unname(primary_forms[[model_name]])
  source <- if (form == "quadratic") student_quadratic else student_linear
  coefficient <- source[source$model_label == model_name, ]
  x_million <- seq(1, 10, length.out = 451)
  seconds <- coefficient$intercept +
    coefficient$linear * x_million +
    coefficient$quadratic * x_million^2
  extrapolation_rows[[length(extrapolation_rows) + 1]] <- data.frame(
    model_label = model_name,
    form = form,
    input_million_tokens = x_million,
    ttft_minutes = seconds / 60
  )
}
extrapolation <- do.call(rbind, extrapolation_rows)
extrapolation$model_label <- factor(extrapolation$model_label, levels = model_order)
endpoints <- extrapolation[extrapolation$input_million_tokens == 10, ]
endpoints$endpoint_label <- sprintf(
  "%s · %.1f min", endpoints$model_label, endpoints$ttft_minutes
)

extrapolation_panel <- ggplot(
  extrapolation,
  aes(
    x = input_million_tokens, y = ttft_minutes,
    color = model_label, group = model_label
  )
) +
  geom_line(linewidth = 1.2, linetype = "dashed", lineend = "round") +
  geom_text(
    data = endpoints,
    aes(x = 10.12, y = ttft_minutes, label = endpoint_label, color = model_label),
    hjust = 0, vjust = 0.5,
    family = font_family, fontface = "bold", size = 3.8,
    show.legend = FALSE, inherit.aes = FALSE
  ) +
  scale_color_manual(values = model_colors, drop = FALSE) +
  scale_x_continuous(
    breaks = c(1, 2, 4, 6, 8, 10),
    labels = c("1", "2", "4", "6", "8", "10"),
    expand = expansion(mult = 0)
  ) +
  scale_y_continuous(
    breaks = c(0, 5, 10, 15, 20),
    labels = c("0", "5", "10", "15", "20"),
    expand = expansion(mult = 0)
  ) +
  coord_cartesian(xlim = c(1, 10), ylim = c(0, 21), expand = FALSE, clip = "off") +
  labs(
    x = "Input context (million tokens)",
    y = "Time to first token (minutes)"
  ) +
  epoch_theme(TRUE, TRUE, TRUE, TRUE) +
  theme(plot.margin = margin(6, 155, 6, 3, unit = "pt"))

export_figure("figure_4_ttft_extrapolation_primary", 10.8, 7.2, function() {
  grid.newpage()
  draw_epoch_header(
    "Illustrative latency extrapolation to 10 million tokens",
    "Quadratic Student-t fits for GPT-5.6; linear Student-t fits for Claude 5"
  )
  print(
    extrapolation_panel,
    vp = viewport(
      x = unit(0.075, "npc"), y = unit(0.16, "npc"),
      width = unit(0.86, "npc"), height = unit(0.65, "npc"),
      just = c("left", "bottom")
    )
  )
  draw_epoch_footer()
})

cat("Generated Epoch-styled TTFT figures in", output_dir, "\n")
