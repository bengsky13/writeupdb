from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt


@dataclass
class ParsedDocument:
    normalized_text: str
    sections: list[tuple[str | None, str]]
    code_blocks: list[tuple[str | None, str]]


def parse_content(content: str, content_format: str) -> ParsedDocument:
    if content_format == "markdown":
        return parse_markdown(content)
    if content_format == "html":
        return parse_html(content)
    if content_format == "json":
        return parse_text(json.dumps(json.loads(content), indent=2, sort_keys=True))
    if content_format == "jsonl":
        return parse_text(content)
    return parse_text(content)


def parse_pdf_bytes(pdf_bytes: bytes) -> ParsedDocument:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
    return parse_text(text)


def parse_markdown(content: str) -> ParsedDocument:
    md = MarkdownIt()
    tokens = md.parse(content)
    sections: list[tuple[str | None, str]] = []
    code_blocks: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for token in tokens:
        if token.type == "heading_open":
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
        elif token.type == "inline" and token.map:
            current_heading = token.content if current_heading != token.content else current_heading
            current_lines.append(token.content)
        elif token.type == "fence":
            code_blocks.append((token.info or None, token.content))
            current_lines.append(token.content)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    normalized = "\n\n".join(text for _, text in sections if text.strip()) or content
    return ParsedDocument(normalized, sections or [(None, content)], code_blocks)


def parse_html(content: str) -> ParsedDocument:
    soup = BeautifulSoup(content, "html5lib")
    for element in soup(["script", "style", "noscript", "iframe", "footer", "nav"]):
        element.decompose()
    headings = soup.find_all(re.compile("^h[1-6]$"))
    sections: list[tuple[str | None, str]] = []
    code_blocks: list[tuple[str | None, str]] = []
    for heading in headings:
        texts: list[str] = []
        for sibling in heading.next_siblings:
            if getattr(sibling, "name", None) and re.match(r"^h[1-6]$", sibling.name):
                break
            if getattr(sibling, "get_text", None):
                texts.append(sibling.get_text(" ", strip=True))
                for code in sibling.find_all(["pre", "code"]):
                    code_blocks.append((code.get("class", [None])[0], code.get_text("\n", strip=False)))
        sections.append((heading.get_text(" ", strip=True), "\n".join(filter(None, texts)).strip()))
    normalized = soup.get_text("\n", strip=True)
    return ParsedDocument(normalized, sections or [(None, normalized)], code_blocks)


def parse_text(content: str) -> ParsedDocument:
    sections = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in content.splitlines():
        if re.match(r"^(#+|\d+\.)\s+", line):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = re.sub(r"^(#+|\d+\.)\s+", "", line).strip()
        current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    code_blocks = [(None, block) for block in re.findall(r"```.*?\n(.*?)```", content, re.S)]
    return ParsedDocument(content, sections or [(None, content)], code_blocks)


def parse_file(path: Path, content_format: str) -> ParsedDocument:
    if content_format == "pdf":
        return parse_pdf_bytes(path.read_bytes())
    return parse_content(path.read_text(encoding="utf-8"), content_format)

