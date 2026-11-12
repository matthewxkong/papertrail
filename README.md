> **Illustrative Git calendar:** 2024-01-08 through 2024-11-22, assigned November 6, 2026.
> Actual development occurred in November 2026. These dates are simulated,
> not evidence of historical work or employment. This supersedes older
> statements below about actual Git dates. See [HISTORY.md](HISTORY.md).

# Papertrail

A personal evidence workspace with a dependency-free Python server and a responsive vanilla web interface. Sample notes demonstrate private and workspace access, retrieval with source versions, and an explicit proposal → approval → execution flow.

## Run locally

Requires Python 3.10+ with SQLite. From this directory:

```powershell
python server.py --port 8762
```

Open http://127.0.0.1:8762. `--db PATH` selects a separate database. The default SQLite database is created beside the server and excluded from version control. `/api/health` is a read-only health endpoint.

```powershell
python -m unittest discover -s tests -v
```

No package installation, accounts, external assets, or network access is needed for the default experience. Sample data is inserted once, not recreated after deletion.

## How it works

- The demo persona selector creates an opaque in-memory session cookie. The server resolves the persona and workspace; retrieval never trusts a client-supplied owner or workspace.
- Access filtering happens **before** retrieval. A temporary FTS5 table contains only authorized documents. When FTS5 is unavailable, token overlap searches the same authorized set.
- Default answers are ranked exact sentence excerpts, not live LLM output. Empty matches explicitly abstain. This is lexical search: common terms can produce weak matches and related words may not match at all. Source IDs and versions identify the text at retrieval time.
- Owners can paste, edit, and remove notes. Editing increments a version and refreshes the index; deletion removes the source. Prior citation text is a snapshot, not a durable source archive. The UI clears displayed evidence on edits, deletions, or persona changes.
- A proposal stores a bounded task title and the current actor/workspace. Approval validates ownership, workspace, and pending status. Execution atomically creates one personal task record, protected by a unique proposal key. Replay and cross-workspace attempts are denied and audited. Dismissal hides the review without executing it.
- Activity is scoped to the current actor. Documents, proposals, tasks, and audit records persist in SQLite. Sessions do not survive server restarts.

## Optional local model seam

If you already have Ollama and a model installed, start:

```powershell
python server.py --model YOUR_INSTALLED_MODEL --ollama-endpoint http://127.0.0.1:11434
```

Then explicitly check the model option before asking. The server sends only the question and already-authorized retrieved excerpts to `/api/chat`. Configuration accepts loopback HTTP origins only; the adapter does not follow redirects, uses a 15-second socket timeout, caps responses at 100 KB, and requests JSON. It downloads nothing. No live model request was made during development validation.

The response must contain bounded answer text, an explicit non-abstention flag, and citations whose document IDs and versions belong to the retrieved evidence. Malformed responses, transport failures, unknown citations, and stale versions cause abstention. `Store.generate` is the integration seam and is mocked in tests.

**Citation validation does not establish semantic truth.** Model text can be wrong or follow malicious text despite the prompt. Always inspect the supplied extracts. The default exact-extract mode is the evidence-first path. Model output never executes actions; task approval remains separate.

## Actual limits

JSON API responses declare their encoded `Content-Length`, including early 400/403 rejections. Closing connections flush and half-close the response before socket teardown. Incoming cleanup is capped at 100,000 bytes and 200 ms, so rejection does not wait indefinitely for a missing request body.

This is an intentionally local **demo identity system, not production authentication or security**. Anyone using the local app can choose any demo persona; the default is Alex. Do not expose the server beyond loopback or use it for sensitive material. Same-origin POST checking and SameSite cookies are defense in depth, not an authentication boundary. There is no CSRF token, password login, encryption, multi-user deployment hardening, rate limiting, or session expiry. A single request worker serializes database operations and approvals. Large workloads will block other requests. No user-supplied paths or URLs are fetched; pasted content is rendered through DOM `textContent`. The optional Ollama endpoint is server configuration, never imported document data.

The sandbox task database has no calendar, email, filesystem, or external task effects. Audit timestamps are actual SQLite UTC timestamps; there are no invented historical activity records. Document version history is not retained after mutation. This project makes no accuracy, legal, compliance, or production readiness claims.

## Demo and review

See [DEMO.md](DEMO.md) for a repeatable walkthrough and the distinction between measured checks and simulated records. See [HISTORY.md](HISTORY.md) for project provenance.
