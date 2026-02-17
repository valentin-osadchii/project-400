## SPEC.md — Confluence page → Markdown (Sphinx/MyST)

### 1) Objective
Create a configurable Python CLI that downloads a single Confluence Cloud page by content ID and converts it into a Sphinx/MyST-friendly Markdown file. [support.atlassian](https://support.atlassian.com/confluence/kb/find-the-page-storage-format-in-confluence-cloud-as-a-non-admin/)
The conversion must preserve meaningful content (text, lists, code blocks, PlantUML source, tables, nested structures) using deterministic, recursive rules. [myst-parser.readthedocs](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)

### 2) Non-goals (current phase)
- Do not download or save attachments (files, images, draw.io, etc.); keep links only if present.
- Do not attempt to replicate Confluence UI styling (expand/tabs/panels); keep only their inner content in reading order.
- Do not export child pages; only the given page ID.

### 3) Interfaces & configuration

#### CLI
Example:
- `confluence_export --base-url https://TENANT.atlassian.net/wiki --page-id 123456 --token-env CONFLUENCE_TOKEN --out out/page.md`

Required args:
- `--base-url`: Confluence Cloud base URL (must include `/wiki` if your tenant uses it).
- `--page-id`: numeric/string page ID.
- `--out`: output markdown file path.

Auth:
- Read token from an env var (configurable name, e.g. `CONFLUENCE_TOKEN`).
- Use headers exactly:
  - `{"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}`

Fetch mode:
- Config option `api_mode: v2|v1` (default `v2`).
- v2 fetch MUST use: `GET /wiki/api/v2/pages/{id}?body-format=storage`. [support.atlassian](https://support.atlassian.com/confluence/kb/find-the-page-storage-format-in-confluence-cloud-as-a-non-admin/)
- v1 fallback MUST use: `GET /wiki/rest/api/content/{id}?expand=body.storage`. [support.atlassian](https://support.atlassian.com/confluence/kb/find-the-page-storage-format-in-confluence-cloud-as-a-non-admin/)

MyST/Sphinx assumptions:
- Internal section links for hoisted blocks rely on MyST heading anchors (document that Sphinx config should set `myst_heading_anchors` to a value ≥ 3). [myst-parser.readthedocs](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)

### 4) Processing pipeline (algorithmic)

#### Step A — Fetch
- Call the configured endpoint.
- Fail clearly on 401/403 (auth) and 404 (page not found).
- Retry with exponential backoff on 429 and transient 5xx.

#### Step B — Parse and normalize
- Treat the returned `storage` body as XHTML-based XML with Confluence custom elements/macros. [confluence.atlassian](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
- Parse into an in-memory DOM/AST.
- Normalize:
  - Remove UI-only wrapper elements but keep and recursively process their children.
  - Preserve order of nodes as they appear.

#### Step C — Convert to Markdown (recursive walk)
Implement a recursive function `convert(node) -> md_chunks[]`:
- Paragraphs/headings/lists: convert to equivalent Markdown.
- Links: keep as Markdown links; do not download targets.
- Code blocks:
  - Convert Confluence code macro or `<pre><code>` to fenced code blocks.
  - Preserve exact text; apply language tag when known.
- PlantUML:
  - When raw PlantUML source is present, emit fenced block with language `plantuml`.
- Unknown macros:
  - Emit a placeholder block that includes macro name + parameters (as readable text) and then the recursively converted inner content, so content is not lost.

Output:
- Emit a single Markdown document with stable ordering.
- Avoid emitting HTML unless explicitly allowed by a future flag (default: Markdown only).

### 5) Tables (merged cells + hoisting)

#### 5.1 Table parsing and grid model
For every `<table>` encountered:
- Assign a table ID in traversal order: `T1`, `T2`, `T3`, …
- Parse rows and cells, reading `rowspan` and `colspan`.
- Build a full rectangular grid (expand spans into covered coordinates).

#### 5.2 Merged cell rule (simplified, no duplication)
For any cell with `rowspan > 1` and/or `colspan > 1`:
- Put converted content only into the origin (top-left) cell.
- All covered cells MUST be emitted as empty cell content.
- Append span metadata marker to the origin cell content:
  - `⟦rowspan=X,colspan=Y⟧` (omit fields that equal 1).

#### 5.3 Hoist complex cell content (mandatory)
A cell is “complex” and MUST be hoisted if its converted content includes any of:
- Nested table output.
- Fenced code block (any language).
- PlantUML fenced block.
- Any block element requiring multi-line Markdown (lists, multiple paragraphs, etc.).

Hoisting procedure:
1) Replace the cell content with:
   - `See: [Tn-RrCc-block-k](#tn-rrcc-block-k)`
2) Append (immediately after the table) a new section in encounter order:
   - Heading line: `### Tn-RrCc-block-k`
   - Then the extracted content rendered normally (and recursively).
3) `Tn-RrCc-block-k` format is strictly positional:
   - `n` = table number, `r` = row index (1-based), `c` = column index (1-based), `k` = hoist counter within that cell (1-based).

Anchor expectation:
- MyST creates heading anchor slugs by lowercasing/removing punctuation/spaces→`-`, so `### T1-R2C3-block-1` becomes `#t1-r2c3-block-1`. [myst-parser.readthedocs](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)

#### 5.4 Nested tables
- Nested tables inside hoisted blocks are processed with the same table algorithm (new table IDs continue incrementing in traversal order).

### 6) Output constraints
- Single `.md` output file.
- No attachment files saved.
- Deterministic output: given the same Confluence input, the output must be byte-stable (except for timestamps if you add them—prefer not to).

### 7) Deliverables
- `confluence_export.py` (or package module) with CLI.
- Config schema (YAML/JSON) documenting all options.
- Fixture-based tests:
  - Input: provided HTML/storage samples.
  - Expected: golden Markdown files.
  - A warnings report for unknown macros or lossy conversions.

### 8) Examples and fixtures

#### 8.1. Exported html-page

Path: `./examples/body-storage/`

#### 8.2. PDF of page from 8.1

Path: `./examples/PDF/`

#### 8.3. Exisiting python-script and resulting md-files 

`./examples/exporter-scripts`

***
