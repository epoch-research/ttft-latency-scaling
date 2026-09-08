# Figure exports

- `publication/` contains the authoritative Messina Sans PNG and SVG exports
  used for the blog.
- `reproduced/` contains portable Inter renders created by
  `Rscript analysis/figures.R`.
- The PNG and SVG files at this directory's top level are convenience copies of
  the authoritative publication exports.

The two versions use identical observations, coefficients, axes, colors, and
layouts. Typography can shift slightly because Messina Sans is not redistributed
in this repository. Portable rendering also emits PDF files; the
blog release artifacts are the PNG and SVG files.
