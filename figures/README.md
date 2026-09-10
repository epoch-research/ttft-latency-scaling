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

## Astra API supplement

`astra-api/astra_api_student_t.{png,svg,pdf}` is a separate single-model figure
using all 24 September 9 Astra API measurements and their Student-t quadratic fit.
It follows the same neutral styling and uses no additional assets. Run
`make astra` to refit and render, or `make astra-figures` to render from the
committed tables. See [`docs/astra-api.md`](../docs/astra-api.md) for provenance
and the treatment of the interrupted initial session and excluded setup requests.
