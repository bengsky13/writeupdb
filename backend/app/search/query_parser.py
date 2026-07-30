from __future__ import annotations

import re

ALIASES = {
    "sqli": "SQL injection",
    "ssti": "server-side template injection",
    "xxe": "XML external entity",
    "uaf": "use-after-free",
    "bof": "buffer overflow",
    "rop": "return-oriented programming",
    "fsop": "file stream oriented programming",
    "prng": "pseudo-random number generator",
    "idor": "insecure direct object reference",
    "lfi": "local file inclusion",
    "rfi": "remote file inclusion",
    "jwt": "JSON Web Token",
    "ret2libc": "return to libc",
    "xss": "cross-site scripting",
    "csrf": "cross-site request forgery",
    "ssrf": "server-side request forgery",
}


def parse_query(query: str) -> dict:
    quoted = re.findall(r'"([^"]+)"', query)
    tokens = [token for token in re.split(r"\s+", re.sub(r'"[^"]+"', "", query).strip()) if token]
    techniques = [ALIASES[token.lower()] for token in tokens if token.lower() in ALIASES]
    architectures = []
    if re.search(r"\b32[- ]bit\b|\bi386\b", query, re.I):
        architectures.append("i386")
    if re.search(r"\b64[- ]bit\b|\bamd64\b|\bx86_64\b", query, re.I):
        architectures.append("amd64")
    category = None
    if re.search(r"\bflask\b|\bprototype\b|\bssti\b", query, re.I):
        category = "web"
    elif re.search(r"\bheap\b|\bglibc\b|\bret2libc\b", query, re.I):
        category = "pwn"
    constraints = []
    if re.search(r"\bno leak\b", query, re.I):
        constraints.append("no information leak")
    return {
        "raw": query,
        "quoted_phrases": quoted,
        "tokens": tokens,
        "code_like_tokens": [token for token in tokens if re.search(r"[_./()%$]|::", token)],
        "techniques": techniques,
        "architectures": architectures,
        "category": category,
        "constraints": constraints,
    }

