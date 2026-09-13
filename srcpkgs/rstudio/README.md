# RStudio Desktop on Void

This recipe packages RStudio 2026.09.0+174 (commit
`870df5ed7859c758db7aed6f510a3edca3c74bd7`) for native x86_64 glibc.
It uses the separately packaged Electron 42 runtime. Qt is not used.

## Dependencies

| Dependency | Role and selection |
| --- | --- |
| electron42, electron42-devel | Desktop runtime and native-addon headers; tested build target is 42.11.3, upstream requests 42.11.1. |
| nodejs | System Node 24 for frontend compilation, native-addon build tools, and session Node helpers. Electron's embedded Node does not replace the session executable. |
| R | Build-time discovery and runtime session. This branch provides 4.6.0; upstream requires at least 3.6.0. |
| OpenJDK 17, Ant | Build the GWT interface. Neither is an application runtime dependency. |
| Python 3, lxml | Build-time i18n generation and node-gyp. pytest is only needed for the generator's tests. |
| npm, Yarn | Build dependencies, installed using upstream lockfiles. Acquisition occurs during configuration; compilation uses the persistent caches offline. |
| Custom GWT 2.12.2 | Upstream's release-specific Java SDK, including its companion Java libraries, from a checksummed archive. |
| Panmirror | Required visual-editor frontend. Its Quarto monorepo source is pinned to a commit; this is distinct from the optional Quarto CLI. |
| Boost 1.91, SOCI 4.0.3, yaml-cpp 0.8 | System C++ libraries matching upstream requirements. SOCI core and SQLite are used by Desktop. Void's soci packages also pull other database backends transitively. |
| libgit2-1.9 | System 1.9.7 satisfies the upstream 1.9.2 requirement. CMake uses pkg-config and the shared library. |
| fmt, Hunspell | System fmt 12.1 and Hunspell 1.7.2; the package patches upstream's fetched-library assumptions. |
| OpenSSL, zlib, libuuid, SQLite | Native system libraries. XBPS adds shared-library runtime requirements from the installed ELF files. |
| DTL, gsl-lite, RapidJSON, tl-expected, UTF8-CPP, WebSocket++ | Upstream commit-pinned headers; WebSocket++ is a fork. Checksummed sources are supplied to CMake FetchContent locally. |
| GoogleTest | Source-pinned C++ test dependency; replaces the old recipe's Catch2 download. Test executables are not installed. |
| Pandoc | System 3.6, used for visual editing and document rendering; replaces upstream's bundled 3.2. |
| Dictionaries | Checksummed data used by the spellchecker; not interchangeable with the Hunspell library itself. |
| procps-ng | Required runtime process utilities, including `ps` for checking whether file-lock owners are alive. |
| lsof | Check-only dependency for the process-working-directory fallback test; Linux normally uses procfs. |
| mathjax2 | System 2.7.9 assets for local R Markdown HTML documents. |
| mathjax | System 4.1.3 assets for inline math, including local New Computer Modern font resources. |

## Optional features

* `QUARTO_ENABLED=OFF` disables the bundled Quarto distribution, not integration
  with an external Quarto CLI. RStudio can discover a user installation.
* `RSTUDIO_ENABLE_AI_FEATURES=OFF` removes Copilot and Posit Assistant support.
  The Copilot language-server archive is not downloaded or installed.
* Git/SVN executables, TeX tools, Python environments, libclang, and R packages
  such as rmarkdown, knitr, renv, and Rcpp serve particular user workflows.
  They are not all required to start the IDE. A tool may nevertheless be present
  through a build dependency or another package's runtime dependencies.
* libclang enables C/C++ source intelligence; RStudio dynamically discovers it.
* PAM and the PostgreSQL SOCI backend are server/pro requirements, not direct
  dependencies of this desktop build. The recipe does not build RStudio Server.
* Qt5, Qt6, Qt SQL plugins, the obsolete Pango declaration, and Catch2 are absent.

## Layout and patches

`/usr/bin/rstudio` launches `/usr/bin/electron42` with the application at
`/usr/lib/rstudio/resources/app`. Native session executables and resources retain
their relative upstream layout. Node, Pandoc, and MathJax resources refer to their
system packages rather than duplicated executables or asset trees.

The patches adapt CMake imported targets and staged dependency sources, preserve
the desktop build directory during reconfiguration, and build with system tools.
The desktop bootstrap selects installed-app behavior when launched through system
Electron. New windows launch the wrapper, and the application argument is removed
before RStudio interprets file arguments. Desktop integration and SOURCE metadata
are adjusted for the distribution layout and release archive.

The memory-metrics test patch accounts for swap capacity when checking Linux's
proc-meminfo provider: its used-memory metric deliberately includes swap, while
its total-memory metric reports physical RAM. No runtime calculation is changed.

Forge consumes a local zip made from electron42 solely as a packaging input.
Only the application payload is installed. Upstream's fuse rewriting is skipped:
the shared Electron binary belongs to electron42. The wrapper does not disable
the Chromium sandbox.

MathJax 4 lives under `/usr/share/mathjax4`; mathjax2 retains `/usr/share/mathjax`.
The mathjax3 compatibility package provides `/usr/share/mathjax3` for Calibre's
version-3 bundler. All three generations can be installed together.

## Build and validation

In this workspace, preserve `etc/conf` and use its separate `codex` configuration:

```sh
./xbps-src -c codex -r electron42 -C -n pkg mathjax
./xbps-src -c codex -r electron42 -C -n pkg mathjax3
./xbps-src -c codex -r electron42 -C -n pkg rstudio
```

The named local repository contains electron42 and its development headers.
Inspect local dependencies before using `-I` on retries. Keep the existing source,
Ninja, npm, Yarn, and GWT caches. Do not run concurrent builds of this source tree.

Validation should distinguish source/checksum and patch checks, CMake generation,
frontend and C++ compilation, native-addon loading, installation, XBPS checks,
and sandboxed desktop smoke tests. Exercise the R console, graphics, help,
terminal, project files and second windows, visual editing, spelling, and math
rendering without network access. R Markdown rendering additionally needs the
user's R packages. Test external Quarto discovery separately from startup without
Quarto. ARM, musl, cross builds, and server builds are outside this recipe's scope.

Validated on 2026-09-13: archive checksums, zero-fuzz patch application, complete
frontend/C++ compilation, installation, and XBPS package checks passed. Both CTest
suites passed (15 shared-core cases; 626 enabled core cases, including seven
skips; three additional core cases are disabled upstream). Desktop TypeScript
checking and source-built native-addon loading under Electron 42.11.3 passed.
All four affected templates pass xlint; shell/JavaScript syntax and diff whitespace
checks pass. MathJax 4 and MathJax 3 packages were built successfully, and their
installed file sets do not overlap.

An isolated desktop launch using the staged package, a private home, and the host
X display opened a project with R 4.6.0. Console execution, a rendered plot, local
help content, and a terminal command passed. The launch retained the upstream
renderer sandbox configuration and did not pass `--no-sandbox`; this is not an
independent audit of sandbox enforcement. RStudio displays upstream's missing
Quarto warning but starts and runs R without Quarto. The test application was
closed afterward; no host package installation was performed.

Visual-editor interaction, spelling, offline math rendering, R Markdown rendering,
external Quarto discovery, and second-window behavior have not been exercised
end-to-end. Calibre's MathJax 3 paths and required asset layout were checked, but
Calibre was not rebuilt or launched as part of this validation.
