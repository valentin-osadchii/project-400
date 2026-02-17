# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool that downloads a single Confluence Cloud page by content ID and converts its storage format (XHTML with custom macros) into Sphinx/MyST-compatible Markdown. The full specification is in `SPEC.md`.

## Project Status

Early stage — has a detailed spec (`SPEC.md`) and a reference script (`examples/exporter-script/export-confluence.py`) but no formal project infrastructure yet. The reference script demonstrates basic fetching and conversion but lacks most spec requirements (CLI, retries, table hoisting, unknown macro placeholders, etc.).

## Repository Structure

- `SPEC.md` — authoritative specification for the tool
- `examples/body-storage/` — sample Confluence HTML page (test fixture input)
- `examples/PDF/` — PDF rendering of the sample page (visual reference)
- `examples/exporter-script/export-confluence.py` — reference Python script
- `examples/exporter-script/exported-pages/` — sample output (basic and code-enhanced markdown)

## Key Technical Details

**Confluence storage format** uses XHTML with custom XML namespaces:
- `ac:structured-macro` with `ac:name` attribute for macros (code, plantuml, expand, tabs, etc.)
- `ac:plain-text-body` wrapping CDATA for macro content
- `ac:parameter` for macro configuration
- Tables use standard HTML (`rowspan`/`colspan`) with classes like `confluenceTable`, `confluenceTh`, `confluenceTd`

**Table hoisting algorithm** (Section 5 of SPEC.md) is the most complex part:
- Tables get sequential IDs (T1, T2, ...)
- Merged cells: content in origin cell only, covered cells empty, with `⟦rowspan=X,colspan=Y⟧` markers
- Complex cells (containing nested tables, code blocks, lists, multi-paragraph) must be hoisted out of the table with `See: [Tn-RrCc-block-k](#tn-rrcc-block-k)` references
- Hoisted content appears as `### Tn-RrCc-block-k` sections after the table
- MyST generates anchors by lowercasing and converting spaces/punctuation to hyphens

**Python dependencies** (from reference script): `requests`, `beautifulsoup4` (with `lxml`), `markdownify`

## CLI Target Interface

```
confluence_export --base-url https://TENANT.atlassian.net/wiki \
  --page-id 123456 \
  --token-env CONFLUENCE_TOKEN \
  --out out/page.md
```

API modes: v2 (`/wiki/api/v2/pages/{id}?body-format=storage`) or v1 fallback (`/wiki/rest/api/content/{id}?expand=body.storage`).

## Testing Approach

Spec calls for fixture-based tests: feed sample HTML storage format, compare against golden Markdown files. Test fixtures live in `examples/`.
