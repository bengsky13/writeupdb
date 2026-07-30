from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedValue:
    field: str
    value: str
    confidence: float
    rule_name: str


RULES: list[tuple[str, str, str, float]] = [
    ("tool", r"\bpwntools\b", "pwntools", 0.98),
    ("technology", r"\bFlask\b", "Flask", 0.96),
    ("technique", r"\bSSTI\b|\bjinja2\b|\{\{.*\}\}", "server-side template injection", 0.95),
    ("technique", r"\btcache poisoning\b", "tcache poisoning", 0.98),
    ("technique", r"\bret2libc\b", "return to libc", 0.98),
    ("architecture", r"\bamd64\b|\bx86_64\b", "amd64", 0.93),
    ("architecture", r"\bi386\b|\b32[- ]bit\b", "i386", 0.93),
    ("binary_protection", r"\bFull RELRO\b", "Full RELRO", 0.95),
    ("binary_protection", r"\bNX\b", "NX", 0.95),
    ("tool", r"\bVolatility\b", "Volatility", 0.97),
    ("tool", r"\bzsteg\b", "zsteg", 0.97),
    ("tool", r"\bbinwalk\b", "binwalk", 0.97),
    ("tool", r"\bexiftool\b", "exiftool", 0.97),
    ("cve", r"\bCVE-\d{4}-\d{4,7}\b", "cve", 0.99),
]


def extract_metadata(text: str) -> list[ExtractedValue]:
    results: list[ExtractedValue] = []
    for field, pattern, value, confidence in RULES:
        for match in re.finditer(pattern, text, flags=re.I):
            extracted = match.group(0) if value == "cve" else value
            results.append(ExtractedValue(field, extracted, confidence, pattern))
    return results

