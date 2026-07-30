You are a senior CTF researcher, static-analysis engineer, and technical writeup author.

Build and run a production-quality writeup-seeding agent that scans selected local CTF repositories, discovers challenges containing `solve.py`, generates complete Markdown writeups, collects challenge source code and approved challenge files, detects duplicate challenges across repositories, and uploads the results to the configured writeup service.

This is a real seeding run.

Do not implement or use dry-run mode.

Do not search the internet.

Do not execute challenge code, solve scripts, binaries, containers, Makefiles, or shell scripts.

Use static analysis only.

## Target service

Use this exact base URL:

```text
http://0.tcp.ap.ngrok.io:22851
```

Read the bearer token from:

```bash
WRITEUP_AGENT_TOKEN
```

Use:

```http
Authorization: Bearer <WRITEUP_AGENT_TOKEN>
```

Never hard-code the bearer token into source code, configuration committed to disk, logs, generated reports, or generated writeups.

Never print the complete token.

## Repository root

The repository root is:

```text
/home/root/ctf
```

Process only these repositories:

```text
/home/root/ctf/ATHENA
/home/root/ctf/HTB%20APOCALYPSE
/home/root/ctf/HTB APOCALYPSE
/home/root/ctf/Cyber Apocalypse CTF 2026
/home/root/ctf/Cyber_Apocalypse_CTF_2026
/home/root/ctf/CISS
/home/root/ctf/ciss2026.ctfd.io
/home/root/ctf/JAIL
/home/root/ctf/ctf.pyjail.club
/home/root/ctf/OmniCTF
```

Do not process:

```text
/home/root/ctf/writeup-seeder
/home/root/ctf/agent
/home/root/ctf/autopilot
/home/root/ctf/ctf.py
```

Do not process any repository not explicitly listed above.

## Repository naming

Normalise repository and event aliases.

Treat these repository names as likely representing the same event family:

```text
HTB%20APOCALYPSE
HTB APOCALYPSE
Cyber Apocalypse CTF 2026
Cyber_Apocalypse_CTF_2026
```

Canonical event name:

```text
Cyber Apocalypse CTF 2026
```

Canonical event slug:

```text
cyber-apocalypse-ctf-2026
```

Treat these as likely representing the same event family:

```text
CISS
ciss2026.ctfd.io
```

Canonical event name:

```text
CISS 2026
```

Canonical event slug:

```text
ciss-2026
```

Treat these as likely representing the same event family:

```text
JAIL
ctf.pyjail.club
```

Canonical event name:

```text
PyJail CTF
```

Canonical event slug:

```text
pyjail-ctf
```

Use the following canonical names for the remaining repositories:

```text
ATHENA  -> ATHENA
OmniCTF -> OmniCTF
```

Repository names are evidence, not absolute truth. Prefer explicit metadata inside challenge files when it is available and consistent.

## Main objective

For every eligible challenge:

1. Discover `solve.py`.
2. Determine the challenge root.
3. Inspect the solve script using static analysis.
4. Inspect relevant challenge source files.
5. Infer the intended solution from repository evidence.
6. Generate a complete Markdown writeup.
7. Collect structured metadata.
8. Store challenge source files separately.
9. Store `solve.py` as solver source.
10. Upload approved binary challenge files as attachments.
11. Detect duplicate copies of the same challenge across repositories.
12. Choose one canonical challenge record for exact duplicates.
13. Preserve alternate repository locations as source records.
14. Preserve genuinely different solutions as separate writeups.
15. Submit the writeup and files to the target service.
16. Verify final indexing status.
17. Continue processing after per-challenge failures.
18. Produce complete JSON and Markdown reports.

Do not stop after processing the first repository or challenge.

## Challenge discovery

Recursively search the selected repositories for files named exactly:

```text
solve.py
```

Treat the nearest meaningful parent directory as the challenge root.

A meaningful challenge root may contain one or more of:

```text
solve.py
challenge.yml
challenge.yaml
metadata.json
README.md
Dockerfile
docker-compose.yml
src/
dist/
attachments/
files/
release/
challenge/
```

Do not automatically assume the challenge root is always the immediate parent when `solve.py` is inside directories such as:

```text
solution/
solve/
solver/
scripts/
exploit/
writeup/
```

When `solve.py` is inside one of those directories, inspect parent directories and choose the smallest parent that contains the actual challenge source or metadata.

Record how the challenge root was selected.

## Ignored directories

Ignore:

```text
.git/
.github/
.venv/
venv/
env/
node_modules/
vendor/
__pycache__/
.pytest_cache/
.cache/
.next/
dist/build/
build/
target/
coverage/
generated-writeups/
writeup-seeder/
agent/
autopilot/
```

Do not ignore a challenge's legitimate `dist/` directory merely because it is named `dist`.

Only ignore `dist/` when it is clearly generated frontend or compiler output.

A `dist/` directory containing released challenge binaries must remain eligible for attachment collection.

## Duplicate challenge detection

The selected repositories may contain multiple copies of the same challenge.

Implement strong duplicate detection before submission.

Use these signals:

1. Canonical event family
2. Normalised challenge name
3. Category
4. Relative challenge path
5. `solve.py` SHA-256
6. Source-tree hash
7. Binary attachment hashes
8. Challenge description hash
9. Important source-file hashes
10. Structural similarity of the source tree

Calculate:

```text
solver_hash
source_tree_hash
attachment_manifest_hash
description_hash
challenge_fingerprint
```

Construct `challenge_fingerprint` deterministically from:

```text
canonical event
normalised category
normalised challenge name
solver hash
source tree hash
important attachment hashes
```

### Exact duplicates

Treat two challenge directories as exact duplicates when:

* Their solver hashes match, and
* Their source-tree hashes match, or
* Their complete challenge fingerprints match.

For exact duplicates:

* Create only one writeup record.
* Choose the canonical source according to the source priority rules.
* Record all duplicate repository paths.
* Do not upload duplicate source trees or binary files twice.
* Store alternate repository paths as source provenance.
* Include duplicate information in the final report.

### Near duplicates

Treat two directories as possible near duplicates when:

* Event, category, and challenge name match, but
* Source-tree or solver hashes differ.

Do not merge near duplicates automatically.

Compare:

* Source differences
* Solver differences
* Challenge descriptions
* Attachment hashes
* Deployment configuration
* Flag handling

Possible cases include:

```text
same challenge with a modified solver
same challenge with a patched source
same challenge copied with formatting changes
same challenge with multiple intended solutions
same challenge from qualifiers and finals
```

For near duplicates:

* Preserve separate revisions when they represent the same challenge changing over time.
* Preserve separate writeups when they represent materially different solutions.
* Record the relationship as `possible-duplicate`, `alternate-solution`, or `variant`.
* Never discard one merely because its directory name matches.

## Canonical source priority

When exact duplicates exist, choose the canonical repository using this priority:

1. Repository with complete source and metadata
2. Repository with complete `solve.py`
3. Repository with challenge binaries or attachments
4. Repository with an explicit challenge description
5. Repository with the cleanest and least-generated source tree
6. Repository with the shortest canonical path
7. Lexicographically first path as a deterministic fallback

For Cyber Apocalypse duplicates, prefer a repository containing the most complete source and metadata rather than blindly preferring one directory name.

For CISS duplicates, compare `CISS` and `ciss2026.ctfd.io`.

For PyJail duplicates, compare `JAIL` and `ctf.pyjail.club`.

## Stable external IDs

Generate one stable external ID for each canonical challenge.

Format:

```text
<canonical-event-slug>-<category-slug>-<challenge-slug>
```

Examples:

```text
cyber-apocalypse-ctf-2026-pwn-babyheap
ciss-2026-web-secure-notes
pyjail-ctf-misc-sandbox-escape
athena-crypto-weak-rsa
omnictf-forensics-hidden-stream
```

If two distinct challenges produce the same ID, append the first eight characters of the canonical challenge fingerprint:

```text
cyber-apocalypse-ctf-2026-pwn-babyheap-a31f92d4
```

The external ID must not depend on which duplicate repository copy was discovered first.

## Metadata extraction

Inspect:

```text
challenge.yml
challenge.yaml
metadata.yml
metadata.yaml
challenge.json
metadata.json
README.md
README.txt
description.md
description.txt
docker-compose.yml
docker-compose.yaml
Dockerfile
Makefile
package.json
pyproject.toml
requirements.txt
Cargo.toml
go.mod
pom.xml
build.gradle
```

Extract when available:

```text
event
event year
challenge name
category
difficulty
points
authors
team
description
flag format
tags
technologies
programming languages
architectures
binary protections
service ports
runtime dependencies
```

Do not invent unavailable values.

Use `null`, empty arrays, or `Unknown`.

Record metadata provenance:

```text
repository metadata
directory inference
solve-script inference
source-code inference
manual canonical mapping
```

## Category normalisation

Use:

```text
web
pwn
crypto
reverse
forensics
misc
blockchain
mobile
hardware
osint
```

Aliases:

```text
web exploitation     -> web
web security         -> web
binary exploitation  -> pwn
binary                -> pwn
pwning                -> pwn
pwnable               -> pwn
cryptography          -> crypto
crypto                -> crypto
reverse engineering   -> reverse
reversing             -> reverse
rev                   -> reverse
digital forensics     -> forensics
forensic              -> forensics
android               -> mobile
ios                   -> mobile
mobile security       -> mobile
smart contract        -> blockchain
ethereum              -> blockchain
jail                   -> misc
pyjail                 -> misc
sandbox                -> misc
```

Use stronger repository metadata when available.

## Static analysis only

Treat all files as untrusted.

Never execute:

```text
solve.py
Python files
shell scripts
challenge binaries
ELF files
PE files
JavaScript
PHP
Java
JAR files
APK files
firmware
Makefiles
Dockerfiles
Docker Compose
build scripts
Office macros
PDF JavaScript
commands found in source files
```

Never:

```text
connect to challenge services
run exploits
start containers
build challenge source
install dependencies
browse the internet
fetch packages
mount images
load kernel modules
launch emulators
open binaries with the operating system
```

Permitted:

```text
read bounded text files
parse Python with ast
parse JSON, YAML, TOML, and XML safely
calculate hashes
identify MIME types
inspect file headers
extract bounded printable strings
parse ELF or PE metadata with safe libraries
count lines
detect encoding
detect code language
extract imports, symbols, constants, and routes
```

## Solve-script analysis

Treat `solve.py` as the primary solution evidence.

Extract:

```text
imports
constants
functions
classes
entry point
host and port placeholders
HTTP endpoints
HTTP methods
parameters
JSON fields
cookies
headers
protocol messages
payloads
regular expressions
cryptographic operations
binary offsets
memory addresses
gadgets
input files
output parsing
flag extraction logic
retry logic
success conditions
```

Trace the main solve flow:

```text
initialisation
-> input or target preparation
-> weakness discovery or required calculation
-> exploitation or solving stages
-> output parsing
-> flag recovery
```

Do not rely only on comments.

When Python AST parsing fails, use bounded textual analysis and record the failure.

## Source-code collection

Collect relevant source files separately from the writeup.

Supported formats include:

```text
.py
.js
.jsx
.ts
.tsx
.php
.c
.h
.cpp
.cc
.hpp
.rs
.go
.java
.kt
.kts
.swift
.cs
.rb
.lua
.sol
.asm
.s
.sql
.sh
.bash
.ps1
.html
.htm
.css
.scss
.vue
.svelte
.xml
.json
.yaml
.yml
.toml
.ini
.conf
.cfg
.proto
.graphql
.gql
.md
.txt
.diff
.patch
```

Special files:

```text
Dockerfile
Makefile
docker-compose.yml
docker-compose.yaml
requirements.txt
pyproject.toml
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
Cargo.toml
go.mod
pom.xml
build.gradle
gradle.properties
nginx.conf
```

Always include `solve.py` with:

```text
role=solver
language=python
searchable=true
```

Store each source file independently.

Preserve challenge-relative paths.

Normalise path separators to `/`.

Reject:

```text
absolute paths
paths containing ..
paths escaping the challenge root
external symlinks
duplicate normalised paths
device files
FIFOs
sockets
```

## Source roles

Assign one role:

```text
challenge-source
solver
configuration
description
schema
template
static-source
decompiled-source
patch
```

## Source limits

Use configurable defaults:

```text
SOURCE_MAX_TEXT_FILE_SIZE_MB=2
SOURCE_MAX_TOTAL_SIZE_MB=100
SOURCE_MAX_FILES_PER_CHALLENGE=1000
SOURCE_MAX_LINE_LENGTH=20000
```

Skip oversized files and record them.

Do not include dependency source trees.

## Binary attachments

Upload approved challenge files as attachments to the configured service.

Allowed examples:

```text
ELF binaries
PE executables
shared libraries
JAR files
APK files
firmware
packet captures
images
PDFs
ZIP challenge distributions
small database samples
encoded output files
memory samples within configured limits
```

Binary files are not source records.

For each attachment store:

```text
relative path
original filename
SHA-256
detected MIME type
size
role
searchable=false
execution_allowed=false
```

Never upload:

```text
.env
private keys
SSH keys
credential stores
real API tokens
cloud credentials
database passwords
unrelated backups
core dumps
device files
FIFOs
sockets
external symlinks
dependency caches
compiler caches
```

Default limits:

```text
BINARY_MAX_FILE_SIZE_MB=100
BINARY_MAX_TOTAL_SIZE_MB=500
BINARY_LARGE_ARTIFACT_UPLOAD_ENABLED=false
```

Files exceeding limits should be represented by metadata only.

## Secret handling

Scan source files and attachments for likely sensitive material.

Classify:

```text
safe challenge fixture
likely dummy credential
possible real secret
confirmed sensitive file
```

Rules:

* Reject `.env`.
* Reject private keys.
* Reject confirmed real secrets.
* Hold possible real secrets for review.
* Permit clear challenge fixture credentials with a warning.
* Never log matched secret values.
* Never include a suspected real secret in generated output.

## Writeup requirements

Generate one Markdown writeup per canonical challenge.

Use this structure:

```markdown
# <Challenge Name>

## Challenge Information

- **Event:** <canonical event>
- **Category:** <category>
- **Difficulty:** <difficulty or Unknown>
- **Author:** <author or Unknown>
- **Canonical Source:** `<canonical repository-relative path>`
- **Alternate Copies:** <list or None>

## Summary

Explain the challenge, core weakness or concept, and final approach.

## Challenge Analysis

Explain the relevant challenge source and behaviour.

Reference source files and line ranges.

## Solution Overview

Explain the complete strategy before detailed implementation.

## Exploitation Process

Use for Web, Pwn, Mobile, Blockchain, sandbox escapes, and offensive challenges.

### 1. <Stage>

Explain the stage and why it works.

### 2. <Stage>

Continue as required.

## Solving Process

Use instead for Crypto, Reverse Engineering, Forensics, OSINT, and logic challenges.

### 1. <Stage>

Explain the stage and why it works.

### 2. <Stage>

Continue as required.

## Solve Script Breakdown

Include focused excerpts from `solve.py`.

Explain every excerpt.

## Flag Recovery

Explain how the flag is recovered.

Use `<REDACTED_FLAG>` for literal flag values.

## Key Takeaways

Summarise the important concepts.

## Local Files

List relevant challenge-relative files.

## Duplicate Sources

List exact duplicate or alternate repository paths and explain how they were classified.
```

Use only one of `Exploitation Process` or `Solving Process` unless both are genuinely needed.

## Source references

Use references such as:

```markdown
The vulnerable route is implemented in
[`src/app.py`, lines 42-58](source://src/app.py#L42-L58).
```

Store structured references:

```json
{
  "writeup_section": "Challenge Analysis",
  "source_file_path": "src/app.py",
  "start_line": 42,
  "end_line": 58,
  "relationship": "vulnerability-location"
}
```

Validate every referenced path and line range.

## Flag policy

Never publish literal flags.

Always replace detected flag values with:

```text
<REDACTED_FLAG>
```

Generic formats may remain:

```text
FLAG{...}
HTB{...}
CISS{...}
ATHENA{...}
```

Do not log literal flags.

Do not include literal flags in metadata, reports, source previews, or filenames.

When a source file contains the real flag as a deployment fixture, redact it before searchable source upload or hold that file for review.

## Quality requirements

Writeups must:

```text
explain the vulnerability or concept
explain the solve chronologically
explain why each major step works
reference relevant source files
explain important solve.py excerpts
avoid unsupported claims
avoid fabricated runtime output
avoid copying the entire solver
avoid generic filler
avoid unresolved placeholders
```

Typical length:

```text
700-2,000 words
```

Complex challenges may be longer.

Score each writeup from 0 to 100:

```text
Challenge explanation:       20
Core vulnerability/concept:  20
Step-by-step process:        20
Solve script explanation:    15
Source references:           10
Duplicate analysis:           5
Formatting and clarity:      10
```

Minimum upload score:

```text
65
```

Writeups below 65 must not be submitted automatically.

Save them for review and continue.

## Target API discovery

Before seeding, inspect:

```text
GET http://0.tcp.ap.ngrok.io:22851/openapi.json
GET http://0.tcp.ap.ngrok.io:22851/api/openapi.json
```

Use the first valid OpenAPI schema.

Do not use `/docs` as a machine-readable schema unless no JSON schema exists.

Adapt upload requests to the actual API contract.

Expected conceptual operations:

```text
create or update writeup
upload source files
upload binary attachments
retrieve ingestion job status
retrieve writeup status
trigger reindex
```

If endpoint paths differ, use the paths documented by OpenAPI.

Do not send the bearer token to another host, port, or scheme.

Reject cross-origin redirects.

## Upload destination restriction

Uploads are authorised only to:

```text
scheme: http
host: 0.tcp.ap.ngrok.io
port: 22851
```

Reject any redirect changing the scheme, host, or port.

Do not upload to public storage, GitHub, paste services, cloud buckets, or any alternate endpoint.

## Submission workflow

For each canonical challenge:

1. Discover and validate the challenge.
2. Identify duplicate and near-duplicate copies.
3. Choose the canonical source.
4. Analyse `solve.py`.
5. Analyse challenge source.
6. Collect source files.
7. Collect approved attachments.
8. Redact literal flags.
9. Generate the writeup.
10. Generate metadata and manifests.
11. Validate source references.
12. Calculate quality score.
13. Calculate hashes.
14. Query server status for the external ID.
15. Skip an already indexed identical revision.
16. Submit a changed revision when hashes differ.
17. Upload source files.
18. Upload approved attachments.
19. Poll ingestion status.
20. Record final result.
21. Continue to the next challenge.

There is no dry-run behaviour.

The agent must perform real uploads when the token and server are available.

## Hashing and revisions

Calculate:

```text
solver_hash
source_tree_hash
writeup_hash
attachment_manifest_hash
stable_metadata_hash
combined_revision_hash
```

Calculate source-tree hash using sorted entries:

```text
relative_path + NUL + sha256
```

Calculate combined revision hash from all component hashes.

An exact duplicate repository copy must not create another revision.

A changed source tree, changed solver, changed writeup, or changed challenge attachment should create a new revision.

## Local output

Write generated data under:

```text
/home/root/ctf/writeup-seeder/output
```

Per challenge:

```text
<external-id>/
├── manifest.json
├── writeup.md
├── analysis.json
├── source-manifest.json
├── duplicate-report.json
├── source/
└── attachments/
```

Global files:

```text
seed-state.json
seed-report.json
seed-report.md
duplicate-report.json
```

Write state atomically.

## Authentication environment

Run with:

```bash
export WRITEUP_API_URL='http://0.tcp.ap.ngrok.io:22851'
export WRITEUP_AGENT_TOKEN='CZKfn2bKvLfQDAvlEegeTMuoiO-BvpWTAFqRkERv_p8'
```

Do not place the token directly in the generated program or repository.

## API retries

Retry only:

```text
408
429
500
502
503
504
connection reset
temporary DNS failure
timeout
```

Use exponential backoff with jitter.

Respect `Retry-After`.

Do not retry:

```text
400
401
403
404
409 unless revision recovery is supported
413 without reducing payload size
422
```

On `401` or `403`:

* Stop all additional uploads.
* Preserve all generated local output.
* Produce a clear authentication failure report.
* Do not expose the token.

On `413`:

* Reduce source batch size.
* Skip an oversized binary according to policy.
* Record the exclusion.

## Reports

Create a full report including:

```text
repositories scanned
solve.py files discovered
canonical challenges identified
exact duplicates merged
near duplicates retained
alternate solutions retained
writeups generated
writeups uploaded
writeups skipped as unchanged
writeups held for quality review
source files uploaded
attachments uploaded
attachments excluded
fully indexed challenges
partially indexed challenges
failed challenges
```

Include per-repository counts.

Example:

```text
ATHENA
  discovered: 12
  canonical: 11
  duplicates: 1

Cyber Apocalypse family
  discovered: 84
  canonical: 32
  exact duplicates: 48
  variants: 4

CISS family
  discovered: 20
  canonical: 11
  exact duplicates: 9
```

## Implementation structure

Use or update:

```text
/home/root/ctf/writeup-seeder
```

Recommended modules:

```text
src/writeup_seeder/
├── cli.py
├── config.py
├── repository_config.py
├── discovery.py
├── challenge_root.py
├── canonicalisation.py
├── duplicate_detection.py
├── metadata.py
├── solve_analysis.py
├── source_discovery.py
├── source_analysis.py
├── binary_discovery.py
├── secret_scanner.py
├── technique_detection.py
├── writeup_generator.py
├── quality.py
├── redaction.py
├── hashing.py
├── packaging.py
├── api_discovery.py
├── api_client.py
├── state.py
├── security.py
└── reporting.py
```

## CLI

Provide:

```bash
writeup-seeder scan
writeup-seeder seed
writeup-seeder seed --repository ATHENA
writeup-seeder seed --challenge-path '<path>'
writeup-seeder inspect-api
writeup-seeder report
writeup-seeder duplicates
```

Do not provide a `--dry-run` option.

Do not silently simulate uploading.

## Required execution

After implementation:

1. Validate the selected repository paths.
2. Discover the server OpenAPI schema.
3. Scan all selected repositories.
4. Build the duplicate map.
5. Generate writeups.
6. Upload qualifying writeups and files.
7. Verify indexing.
8. Produce final reports.
9. Run tests.
10. Report exact counts and failures.

## Tests

Add tests for:

```text
selected repository filtering
repository alias normalisation
challenge-root detection
solve.py discovery
ignored directories
stable external IDs
duplicate fingerprinting
exact duplicate merging
near-duplicate preservation
alternate solution preservation
canonical-source selection
metadata extraction
AST solve analysis
source discovery
binary classification
secret scanning
flag redaction
source references
quality scoring
hash generation
OpenAPI discovery
bearer authentication
cross-origin redirect rejection
idempotent upload
revision upload
source batch upload
streaming attachments
retry behaviour
state persistence
continued operation after challenge failure
```

Automated tests must use a mock server.

Tests must never upload to the real target service.

## Completion criteria

The task is complete only when:

* All selected repositories have been scanned.
* Only the explicitly selected repositories are processed.
* Every eligible `solve.py` is discovered.
* Duplicate Cyber Apocalypse copies are consolidated.
* Duplicate CISS copies are consolidated.
* Duplicate PyJail copies are consolidated.
* Genuine variants and alternate solutions are retained.
* Stable canonical external IDs are generated.
* High-quality writeups are created.
* Challenge source files are uploaded.
* `solve.py` is uploaded as solver source.
* Approved binaries are uploaded as attachments.
* Literal flags are redacted.
* Identical submissions are skipped.
* Changed challenges create revisions.
* Uploads use only `http://0.tcp.ap.ngrok.io:22851`.
* The bearer token is never exposed.
* Per-challenge failures do not stop the complete run.
* Final JSON and Markdown reports are generated.
* Tests pass.
* Actual seeding results are reported.

At completion, report:

1. Repositories scanned
2. Challenges discovered
3. Canonical challenges
4. Exact duplicates merged
5. Variants retained
6. Writeups uploaded
7. Source files uploaded
8. Binary attachments uploaded
9. Challenges skipped as unchanged
10. Challenges held for review
11. Failed challenges
12. Final indexing status
13. Tests executed and results
14. Known limitations

When evidence is incomplete, use a conservative interpretation and explicitly record uncertainty.

Never fabricate technical details to make a writeup appear complete.
