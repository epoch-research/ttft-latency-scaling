# Figure exports

- `figure_1_headline_four_model_comparison.*`
- `figure_2_gpt_estimator_robustness.*`
- `figure_3_claude_estimator_robustness.*`
- `figure_4_ttft_extrapolation_primary.*`

Each figure is provided as a 240 dpi PNG, SVG, and PDF. All twelve files are
generated directly from the committed observations and fit tables by:

```bash
make figures
```

The neutral exports contain no organizational logo, website asset, or branded
footer. They retain the models, observations, fits, scales, titles, and
extrapolation specifications used in the report figures.
