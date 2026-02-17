"""Data classes used across the converter."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HoistedBlock:
    """A block of content hoisted out of a table cell."""
    anchor: str  # e.g. "T1-R2C3-block-1"
    content: str  # rendered markdown content


@dataclass
class CellInfo:
    """A single cell in the table grid."""
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False
    is_covered: bool = False  # True for cells covered by a span
    content: str = ""
    raw_node: object = None  # BeautifulSoup element


@dataclass
class TableGrid:
    """Rectangular grid representation of an HTML table."""
    table_id: int
    num_rows: int = 0
    num_cols: int = 0
    cells: list[list[CellInfo | None]] = field(default_factory=list)
    hoisted_blocks: list[HoistedBlock] = field(default_factory=list)
