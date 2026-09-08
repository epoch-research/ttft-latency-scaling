# Third-party materials

The MIT License in [`LICENSE`](LICENSE) applies to Epoch-authored contents of
this repository. It does not replace the terms that apply to the following
third-party materials.

## Inter fonts

The files under `assets/fonts/Inter/` are distributed under the SIL Open Font
License, Version 1.1. The complete license text is included at
`assets/fonts/Inter/OFL.txt`.

## Project Gutenberg source corpus

`data/corpus/combined.txt` is assembled from the seven Project Gutenberg texts
listed in `data/corpus/manifest.json`. Each official catalog entry identifies
the corresponding work as public domain in the United States. The combined file
retains the opening Project Gutenberg use notice and the complete Project
Gutenberg license for every included text.

The preparation code normalizes line endings, trims outer whitespace, inserts a
document heading, and concatenates the texts. The manifest provides the official
source URL and pinned SHA-256 digest for each downloaded file. The repository
provides the combined corpus without charge.

Epoch does not relicense these source texts under the MIT License. Redistribution
remains subject to the notices embedded in each text, the
[Project Gutenberg License](https://www.gutenberg.org/policy/license.html), and
applicable copyright law outside the United States. Project Gutenberg's
[permission guidance](https://www.gutenberg.org/policy/permission.html) explains
the distinction between the public-domain works and its trademark terms.
