"""Tests for the HTML→Markdown converter."""

from pathlib import Path

from confluence_export.converter import convert_html

FIXTURES = Path(__file__).parent / "fixtures"


def test_golden_file():
    """End-to-end: storage HTML → Markdown matches golden file."""
    html = (FIXTURES / "sample_storage.html").read_text()
    expected = (FIXTURES / "sample_expected.md").read_text()
    result = convert_html(html)
    assert result == expected


def test_headings():
    for level in range(1, 7):
        tag = f"h{level}"
        html = f"<{tag}>Title</{tag}>"
        md = convert_html(html)
        assert f"{'#' * level} Title" in md


def test_paragraph():
    md = convert_html("<p>Hello world</p>")
    assert "Hello world" in md


def test_bold():
    md = convert_html("<p><strong>bold text</strong></p>")
    assert "**bold text**" in md


def test_italic():
    md = convert_html("<p><em>italic text</em></p>")
    assert "*italic text*" in md


def test_inline_code():
    md = convert_html("<p>Use <code>foo()</code> here</p>")
    assert "`foo()`" in md


def test_link():
    md = convert_html('<p><a href="https://example.com">click</a></p>')
    assert "[click](https://example.com)" in md


def test_unordered_list():
    md = convert_html("<ul><li>one</li><li>two</li></ul>")
    assert "- one" in md
    assert "- two" in md


def test_ordered_list():
    md = convert_html("<ol><li>first</li><li>second</li></ol>")
    assert "1. first" in md
    assert "2. second" in md


def test_code_macro():
    html = """
    <ac:structured-macro ac:name="code">
      <ac:parameter ac:name="language">python</ac:parameter>
      <ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "```python" in md
    assert 'print("hello")' in md
    assert md.count("```") == 2


def test_plantuml_macro():
    html = """
    <ac:structured-macro ac:name="plantuml">
      <ac:plain-text-body><![CDATA[@startuml
Alice -> Bob
@enduml]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "```plantuml" in md
    assert "Alice -> Bob" in md


def test_drawio_macro():
    html = """
    <ac:structured-macro ac:name="drawio">
      <ac:parameter ac:name="diagramName">my diagram</ac:parameter>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "<!-- drawio: my diagram -->" in md


def test_unknown_macro():
    html = """
    <ac:structured-macro ac:name="somemacro">
      <ac:parameter ac:name="key1">val1</ac:parameter>
      <ac:rich-text-body><p>inner content</p></ac:rich-text-body>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "<!-- unknown macro: somemacro" in md
    assert "key1=val1" in md
    assert "inner content" in md


def test_inline_comment_marker_stripped():
    html = '<p><ac:inline-comment-marker ac:ref="abc">visible text</ac:inline-comment-marker></p>'
    md = convert_html(html)
    assert "visible text" in md
    assert "ac:inline-comment-marker" not in md


def test_ui_tabs():
    html = """
    <ac:structured-macro ac:name="ui-tabs">
      <ac:rich-text-body>
        <ac:structured-macro ac:name="ui-tab">
          <ac:parameter ac:name="title">Tab A</ac:parameter>
          <ac:rich-text-body><p>Tab A content</p></ac:rich-text-body>
        </ac:structured-macro>
      </ac:rich-text-body>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "**Tab A**" in md
    assert "Tab A content" in md


def test_ui_expand():
    html = """
    <ac:structured-macro ac:name="ui-expand">
      <ac:parameter ac:name="title">Expandable</ac:parameter>
      <ac:rich-text-body><p>Hidden content</p></ac:rich-text-body>
    </ac:structured-macro>
    """
    md = convert_html(html)
    assert "**Expandable**" in md
    assert "Hidden content" in md


def test_pre_code_block():
    html = "<pre><code>some code here</code></pre>"
    md = convert_html(html)
    assert "```" in md
    assert "some code here" in md
