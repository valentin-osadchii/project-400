"""Recursive HTML→Markdown converter for Confluence storage format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag, CData, Comment

from confluence_export.tables import build_grid, render_table


@dataclass
class ConverterState:
    """Mutable state carried through the recursive conversion."""
    table_counter: int = 0
    list_depth: int = 0


def convert_html(html: str) -> str:
    """Convert Confluence storage-format HTML to Sphinx/MyST Markdown."""
    soup = BeautifulSoup(html, "html.parser")
    state = ConverterState()
    result = _convert_children(soup, state)
    # Clean up excessive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n"


def _convert_children(node: Tag, state: ConverterState) -> str:
    """Recursively convert all children of a node."""
    parts: list[str] = []
    for child in node.children:
        parts.append(_convert_node(child, state))
    return "".join(parts)


def _convert_node(node, state: ConverterState) -> str:
    """Convert a single DOM node to Markdown."""
    if isinstance(node, (CData, Comment)):
        return ""
    if isinstance(node, NavigableString):
        text = str(node)
        # Collapse whitespace but preserve explicit newlines
        text = re.sub(r"[ \t]+", " ", text)
        return text

    if not isinstance(node, Tag):
        return ""

    tag = node.name

    # --- Headings ---
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        inner = _inline_text(node, state).strip()
        if not inner:
            return ""
        return f"\n\n{'#' * level} {inner}\n\n"

    # --- Paragraphs ---
    if tag == "p":
        inner = _convert_children(node, state).strip()
        if not inner:
            return "\n"
        return f"\n\n{inner}\n\n"

    # --- Line break ---
    if tag == "br":
        return "\n"

    # --- Inline formatting ---
    if tag in ("strong", "b"):
        inner = _convert_children(node, state).strip()
        if not inner:
            return ""
        return f"**{inner}**"

    if tag in ("em", "i"):
        inner = _convert_children(node, state).strip()
        if not inner:
            return ""
        return f"*{inner}*"

    if tag == "code" and not _is_inside_pre(node):
        inner = node.get_text()
        return f"`{inner}`"

    if tag == "pre":
        code_tag = node.find("code")
        if code_tag:
            text = code_tag.get_text()
        else:
            text = node.get_text()
        return f"\n\n```\n{text}\n```\n\n"

    # --- Links ---
    if tag == "a":
        href = node.get("href", "")
        inner = _convert_children(node, state).strip()
        if not inner:
            inner = href
        return f"[{inner}]({href})"

    # --- Images ---
    if tag == "img":
        alt = node.get("alt", "")
        src = node.get("src", "")
        return f"![{alt}]({src})"

    # --- Lists ---
    if tag in ("ul", "ol"):
        return _convert_list(node, state)

    if tag == "li":
        return _convert_children(node, state)

    # --- Tables ---
    if tag == "table":
        state.table_counter += 1
        grid = build_grid(node, state.table_counter, state)
        return "\n\n" + render_table(grid, state, _convert_children) + "\n"

    # --- Confluence macros ---
    if tag == "ac:structured-macro":
        return _convert_macro(node, state)

    # --- Inline comment markers: strip, keep inner text ---
    if tag == "ac:inline-comment-marker":
        return _convert_children(node, state)

    # --- Rich text body / plain text body wrappers ---
    if tag in ("ac:rich-text-body", "ac:plain-text-body"):
        return _convert_children(node, state)

    # --- ac:parameter: skip (handled by macro converter) ---
    if tag == "ac:parameter":
        return ""

    # --- Default: recurse into children ---
    return _convert_children(node, state)


def _is_inside_pre(node: Tag) -> bool:
    for parent in node.parents:
        if isinstance(parent, Tag) and parent.name == "pre":
            return True
    return False


def _inline_text(node: Tag, state: ConverterState) -> str:
    """Convert node to inline markdown (no block-level wrapping)."""
    return _convert_children(node, state)


def _convert_list(node: Tag, state: ConverterState) -> str:
    """Convert <ul> or <ol> to Markdown list."""
    is_ordered = node.name == "ol"
    items: list[str] = []
    counter = 1

    state.list_depth += 1
    indent = "  " * (state.list_depth - 1)

    for child in node.children:
        if isinstance(child, Tag) and child.name == "li":
            content = _convert_li_content(child, state)
            if is_ordered:
                prefix = f"{indent}{counter}. "
                counter += 1
            else:
                prefix = f"{indent}- "
            # Indent continuation lines
            lines = content.split("\n")
            first = lines[0]
            rest = lines[1:]
            cont_indent = " " * len(prefix)
            result_lines = [prefix + first]
            for line in rest:
                if line.strip():
                    result_lines.append(cont_indent + line)
                else:
                    result_lines.append("")
            items.append("\n".join(result_lines))

    state.list_depth -= 1

    result = "\n".join(items)
    if state.list_depth == 0:
        return f"\n\n{result}\n\n"
    return result


def _convert_li_content(li: Tag, state: ConverterState) -> str:
    """Convert the content of an <li>, handling nested lists specially."""
    parts: list[str] = []
    for child in li.children:
        if isinstance(child, Tag) and child.name in ("ul", "ol"):
            parts.append("\n" + _convert_list(child, state))
        else:
            parts.append(_convert_node(child, state))
    return "".join(parts).strip()


def _convert_macro(node: Tag, state: ConverterState) -> str:
    """Convert an ac:structured-macro element."""
    macro_name = node.get("ac:name", "")

    if macro_name == "code":
        return _convert_code_macro(node)

    if macro_name == "plantuml":
        return _convert_plantuml_macro(node)

    if macro_name == "drawio":
        return _convert_drawio_macro(node)

    if macro_name == "ui-tabs":
        # Strip wrapper, process children
        body = node.find("ac:rich-text-body")
        if body:
            return _convert_children(body, state)
        return ""

    if macro_name == "ui-tab":
        title_param = node.find("ac:parameter", attrs={"ac:name": "title"})
        title = title_param.get_text() if title_param else ""
        body = node.find("ac:rich-text-body")
        result = ""
        if title:
            result += f"\n\n**{title}**\n\n"
        if body:
            result += _convert_children(body, state)
        return result

    if macro_name in ("ui-expand", "expand"):
        title_param = node.find("ac:parameter", attrs={"ac:name": "title"})
        title = title_param.get_text() if title_param else ""
        body = node.find("ac:rich-text-body")
        result = ""
        if title:
            result += f"\n\n**{title}**\n\n"
        if body:
            result += _convert_children(body, state)
        return result

    # Unknown macro: emit placeholder + inner content
    return _convert_unknown_macro(node, state)


def _convert_code_macro(node: Tag) -> str:
    """Convert a Confluence code macro to a fenced code block."""
    lang_param = node.find("ac:parameter", attrs={"ac:name": "language"})
    language = lang_param.get_text().strip() if lang_param else ""

    body = node.find("ac:plain-text-body")
    if body:
        # Content may be in CDATA
        code = _extract_cdata_text(body)
    else:
        code = ""

    return f"\n\n```{language}\n{code}\n```\n\n"


def _convert_plantuml_macro(node: Tag) -> str:
    """Convert a PlantUML macro to a plantuml fenced block."""
    body = node.find("ac:plain-text-body")
    if body:
        code = _extract_cdata_text(body)
    else:
        code = ""
    return f"\n\n```plantuml\n{code}\n```\n\n"


def _convert_drawio_macro(node: Tag) -> str:
    """Convert a draw.io macro to a comment placeholder."""
    name_param = node.find("ac:parameter", attrs={"ac:name": "diagramName"})
    name = name_param.get_text().strip() if name_param else "unknown"
    return f"\n\n<!-- drawio: {name} -->\n\n"


def _convert_unknown_macro(node: Tag, state: ConverterState) -> str:
    """Emit a placeholder for an unknown macro, plus its inner content."""
    macro_name = node.get("ac:name", "unknown")
    params = {}
    for p in node.find_all("ac:parameter", recursive=False):
        pname = p.get("ac:name", "")
        pval = p.get_text().strip()
        if pname:
            params[pname] = pval

    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
    comment = f"<!-- unknown macro: {macro_name}"
    if param_str:
        comment += f", params: {param_str}"
    comment += " -->"

    # Also convert inner content so nothing is lost
    inner = ""
    body = node.find("ac:rich-text-body")
    if body:
        inner = _convert_children(body, state)
    plain = node.find("ac:plain-text-body")
    if plain:
        inner += _extract_cdata_text(plain)

    result = f"\n\n{comment}\n"
    if inner.strip():
        result += f"\n{inner.strip()}\n"
    result += "\n"
    return result


def _extract_cdata_text(body_tag: Tag) -> str:
    """Extract text from an ac:plain-text-body, handling CDATA."""
    # BeautifulSoup with lxml parses CDATA as CData or Comment nodes
    for child in body_tag.children:
        if isinstance(child, CData):
            return str(child)
        if isinstance(child, Comment):
            # lxml sometimes wraps CDATA content in Comment nodes
            text = str(child)
            # Strip [CDATA[ and ]] wrappers if present
            if text.startswith("[CDATA["):
                text = text[7:]
            if text.endswith("]]"):
                text = text[:-2]
            return text
    return body_tag.get_text()
