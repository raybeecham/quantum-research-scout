# Bundled math renderer

KaTeX **0.18.7**, from the `katex@0.18.7` npm package (MIT license).
Only the minified browser JS, stylesheet, fonts, and original LICENSE are retained.
Package SHA-1 from npm: `972327a0c0f83be54423c8cc50d0bc3693523fa7`.

These assets are copied unmodified by `scripts/build_dashboard.py`. Versioned
paths pin the browser assets without a runtime CDN or an npm requirement for
building the static site. Do not run formatters over the vendored distribution.

Integration: `dashboard/math.js`. Untrusted TeX is rendered with `trust: false`,
bounded expansion/size, fresh per-expression macros, and visible raw-text fallback.
Notes and exports retain the original source notation.
