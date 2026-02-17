"""Tests for the table algorithm: grid building, hoisting, merged cells."""

from bs4 import BeautifulSoup, Tag

from confluence_export.converter import ConverterState, _convert_children, convert_html
from confluence_export.tables import build_grid, render_table, _is_complex


def _parse_table(html: str) -> Tag:
    soup = BeautifulSoup(html, "html.parser")
    return soup.find("table")


def test_simple_table():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr><td>1</td><td>2</td></tr>
    </table>
    """
    md = convert_html(html)
    assert "| A" in md
    assert "| B" in md
    assert "| 1" in md
    assert "| 2" in md
    assert "---" in md


def test_numbering_column_stripped():
    html = """
    <table>
      <tr><th class="numberingColumn">Nr</th><th>Name</th></tr>
      <tr><td class="numberingColumn">1</td><td>Alice</td></tr>
    </table>
    """
    md = convert_html(html)
    assert "Name" in md
    assert "Alice" in md
    assert "Nr" not in md


def test_colspan():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr><td colspan="2">merged</td></tr>
    </table>
    """
    md = convert_html(html)
    assert "⟦colspan=2⟧" in md
    assert "merged" in md


def test_rowspan():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr><td rowspan="2">span</td><td>r1</td></tr>
      <tr><td>r2</td></tr>
    </table>
    """
    md = convert_html(html)
    assert "⟦rowspan=2⟧" in md
    assert "span" in md


def test_complex_cell_with_code_is_hoisted():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr>
        <td>simple</td>
        <td>
          <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">json</ac:parameter>
            <ac:plain-text-body><![CDATA[{"key": "val"}]]></ac:plain-text-body>
          </ac:structured-macro>
        </td>
      </tr>
    </table>
    """
    md = convert_html(html)
    assert "See: [T1-R2C2-block-1](#t1-r2c2-block-1)" in md
    assert "### T1-R2C2-block-1" in md
    assert "```json" in md
    assert '{"key": "val"}' in md


def test_complex_cell_with_nested_table_is_hoisted():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr>
        <td>simple</td>
        <td>
          <table><tr><th>X</th></tr><tr><td>Y</td></tr></table>
        </td>
      </tr>
    </table>
    """
    md = convert_html(html)
    # The outer table cell should reference a hoisted block
    assert "See:" in md
    assert "block-1" in md


def test_is_complex():
    assert _is_complex("simple text") is False
    assert _is_complex("```python\nprint(1)\n```") is True
    assert _is_complex("para 1\n\npara 2") is True
    assert _is_complex("- item1\n- item2") is True


def test_grid_building():
    html = """
    <table>
      <tr><th>A</th><th>B</th><th>C</th></tr>
      <tr><td colspan="2">AB</td><td>c</td></tr>
    </table>
    """
    table_tag = _parse_table(html)
    state = ConverterState()
    state.table_counter = 0
    grid = build_grid(table_tag, 1, state)
    assert grid.num_rows == 2
    assert grid.num_cols == 3
    # First data row: cell at (1,0) has colspan=2, cell at (1,1) is covered
    assert grid.cells[1][0].colspan == 2
    assert grid.cells[1][1].is_covered is True
