"""Table parsing, grid building, complexity detection, and hoisting."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import Tag

from confluence_export.models import CellInfo, HoistedBlock, TableGrid

if TYPE_CHECKING:
    from confluence_export.converter import ConverterState


# ---------------------------------------------------------------------------
# Global table counter (reset per document via ConverterState)
# ---------------------------------------------------------------------------


def _is_numbering_column(cell: Tag) -> bool:
    classes = cell.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    return "numberingColumn" in classes


def build_grid(table_tag: Tag, table_id: int, state: "ConverterState") -> TableGrid:
    """Parse an HTML <table> into a rectangular TableGrid."""
    rows = []
    for tr in table_tag.find_all("tr", recursive=False):
        rows.append(tr)
    tbody = table_tag.find("tbody", recursive=False)
    if tbody:
        rows = []
        for tr in tbody.find_all("tr", recursive=False):
            rows.append(tr)
    thead = table_tag.find("thead", recursive=False)
    if thead:
        head_rows = list(thead.find_all("tr", recursive=False))
        body_rows = list(tbody.find_all("tr", recursive=False)) if tbody else []
        rows = head_rows + body_rows

    if not rows:
        return TableGrid(table_id=table_id)

    # First pass: determine grid dimensions and collect cells
    raw_cells: list[list[tuple[Tag, bool]]] = []  # (element, is_header)
    for tr in rows:
        row_cells = []
        for child in tr.find_all(["th", "td"], recursive=False):
            if _is_numbering_column(child):
                continue
            row_cells.append((child, child.name == "th"))
        raw_cells.append(row_cells)

    # Determine number of columns
    max_cols = 0
    for row in raw_cells:
        col_count = sum(int(cell.get("colspan", 1)) for cell, _ in row)
        max_cols = max(max_cols, col_count)

    num_rows = len(raw_cells)
    num_cols = max_cols

    # Build the grid
    grid: list[list[CellInfo | None]] = [
        [None for _ in range(num_cols)] for _ in range(num_rows)
    ]

    for r_idx, row in enumerate(raw_cells):
        c_idx = 0
        for cell_tag, is_header in row:
            # Skip cells already filled by a span
            while c_idx < num_cols and grid[r_idx][c_idx] is not None:
                c_idx += 1
            if c_idx >= num_cols:
                break

            rowspan = int(cell_tag.get("rowspan", 1))
            colspan = int(cell_tag.get("colspan", 1))

            info = CellInfo(
                row=r_idx,
                col=c_idx,
                rowspan=rowspan,
                colspan=colspan,
                is_header=is_header,
                is_covered=False,
                raw_node=cell_tag,
            )
            grid[r_idx][c_idx] = info

            # Mark covered cells
            for dr in range(rowspan):
                for dc in range(colspan):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r_idx + dr, c_idx + dc
                    if rr < num_rows and cc < num_cols:
                        grid[rr][cc] = CellInfo(
                            row=rr, col=cc, is_covered=True, is_header=is_header
                        )
            c_idx += colspan

    return TableGrid(
        table_id=table_id,
        num_rows=num_rows,
        num_cols=num_cols,
        cells=grid,
    )


def _is_complex(content: str) -> bool:
    """Return True if cell content is too complex for inline pipe-table rendering."""
    # Nested table marker
    if "|" in content and "---" in content:
        # Heuristic: if we see a pipe-table pattern, it's complex
        lines = content.strip().split("\n")
        if any(re.match(r"^\|.*\|$", line) for line in lines):
            return True
    # Fenced code block
    if "```" in content:
        return True
    # Multiple paragraphs or block elements
    stripped = content.strip()
    if "\n\n" in stripped:
        return True
    # List items
    lines = stripped.split("\n")
    if any(re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+\.\s", line) for line in lines):
        return True
    return False


def render_table(
    grid: TableGrid,
    state: "ConverterState",
    convert_children_fn,
) -> str:
    """Render a TableGrid as a pipe table with hoisting for complex cells.

    convert_children_fn(node, state) -> str  is used to convert cell contents.
    """
    if grid.num_rows == 0 or grid.num_cols == 0:
        return ""

    # Convert all origin cell contents
    cell_texts: list[list[str]] = [
        ["" for _ in range(grid.num_cols)] for _ in range(grid.num_rows)
    ]

    for r in range(grid.num_rows):
        for c in range(grid.num_cols):
            cell = grid.cells[r][c]
            if cell is None or cell.is_covered:
                cell_texts[r][c] = ""
                continue
            # Convert cell content
            raw = convert_children_fn(cell.raw_node, state)
            # Collapse to single line for table cell (strip leading/trailing whitespace)
            content = raw.strip()
            # Add span markers
            span_parts = []
            if cell.rowspan > 1:
                span_parts.append(f"rowspan={cell.rowspan}")
            if cell.colspan > 1:
                span_parts.append(f"colspan={cell.colspan}")
            if span_parts:
                content += f" ⟦{','.join(span_parts)}⟧"

            cell_texts[r][c] = content

    # Hoisting pass
    for r in range(grid.num_rows):
        for c in range(grid.num_cols):
            cell = grid.cells[r][c]
            if cell is None or cell.is_covered:
                continue
            content = cell_texts[r][c]
            # Strip span marker for complexity check
            bare = re.sub(r"\s*⟦[^⟧]*⟧$", "", content)
            if _is_complex(bare):
                span_marker = ""
                m = re.search(r"(\s*⟦[^⟧]*⟧)$", content)
                if m:
                    span_marker = m.group(1)
                    bare = content[: m.start()]

                anchor = f"T{grid.table_id}-R{r+1}C{c+1}-block-1"
                grid.hoisted_blocks.append(
                    HoistedBlock(anchor=anchor, content=bare.strip())
                )
                cell_texts[r][c] = f"See: [{anchor}](#{anchor.lower()}){span_marker}"

    # Render pipe table
    lines: list[str] = []

    # Determine column widths (minimum 3 for separator)
    col_widths = [3] * grid.num_cols
    for r in range(grid.num_rows):
        for c in range(grid.num_cols):
            # Escape pipes in cell content
            text = cell_texts[r][c].replace("\n", " ")
            col_widths[c] = max(col_widths[c], len(text))

    for r in range(grid.num_rows):
        row_parts = []
        for c in range(grid.num_cols):
            text = cell_texts[r][c].replace("\n", " ")
            row_parts.append(f" {text.ljust(col_widths[c])} ")
        lines.append("|" + "|".join(row_parts) + "|")
        # Add separator after first row (header)
        if r == 0:
            sep_parts = [" " + "-" * col_widths[c] + " " for c in range(grid.num_cols)]
            lines.append("|" + "|".join(sep_parts) + "|")

    result = "\n".join(lines) + "\n"

    # Append hoisted blocks
    if grid.hoisted_blocks:
        result += "\n"
        for block in grid.hoisted_blocks:
            result += f"### {block.anchor}\n\n{block.content}\n\n"

    return result
