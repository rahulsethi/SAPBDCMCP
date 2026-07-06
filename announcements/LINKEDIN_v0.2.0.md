# LinkedIn drafts — sap-bdc-mcp v0.2.0 "Governed BDC Connect"

> 5 ready-to-post drafts announcing **SAP BDC MCP v0.2.0**. Each is centered on the BDC MCP
> release and what it adds, and closes with a single line noting the sibling **SAP Datasphere MCP**
> server (announced separately, a few days earlier) follows the same principle.
> Pick one, mix-and-match, or trim to taste.
>
> Accuracy guardrails honored across all drafts:
> - v0.2 ships the **governance rails + a controlled execution surface** (dry-run, approval token,
>   audit, API-policy gate). **Databricks-first**; **Snowflake is readiness-only**; real provider
>   mutation wiring lands in **v0.3**. No claim of live production writes today.
> - Tool count: **25 total** (12 from v0.1 + 13 new).
> - License: **BSL 1.1** (Business Source License → auto-converts to Apache 2.0 on 2029-01-01).

---

## Draft 1 — Main announcement (recommended lead)

Shipping: **SAP BDC MCP v0.2.0 — "Governed BDC Connect."**

v0.1 of my MCP server for SAP Business Data Cloud was contract-first: an agent could read the catalog (ORD), validate CSN contracts, and *plan* a data share — but never actually *do* anything. Safe, but read-only.

v0.2 keeps every one of those promises and adds a small, carefully gated **execution** surface. What's new:

• **25 MCP tools** now (12 discovery/contract tools + 13 new)
• **Provider-neutral execution layer** — Databricks-first, Snowflake readiness
• A **gate chain** on the one mutating tool: write-enable → SAP API-policy evidence → dry-run → constant-time approval token → audited execute
• **JSONL audit log** — every tool call logged with sha256-hashed, redacted inputs
• **Safe by default** — writes off, dry-run required, approval token required, strict API-policy mode, audit on
• Install via **`pip`** or **`npx`**; you can even mount other MCP servers as governed subprocess plugins

The thesis I keep coming back to: enterprises want agents that *act* on SAP data — but real enterprise action needs safe defaults, audit trails, and no undocumented API surprises. Governance isn't a feature you bolt on later; it's the substrate you build capability into.

Link + changelog in the comments. Feedback welcome — especially from people running SAP + AI in production.

P.S. My SAP Datasphere MCP server (announced separately last week) is built on the exact same governed, safe-by-default principle — read-only, for the analytics side of the estate.

#SAP #BusinessDataCloud #MCP #ModelContextProtocol #AgenticAI #EnterpriseAI #Databricks

---

## Draft 2 — Architect deep-dive (for the technical audience)

"Can the agent just run the share?" — the question that shaped **SAP BDC MCP v0.2.0**.

For enterprise SAP, the honest answer isn't "yes" or "no." It's "yes — *through a gate chain you can audit.*"

So that's what v0.2.0 ("Governed BDC Connect") is. Here's the full path for the one write-capable tool, `bdc_share_execute_plan`:

1. WRITE tools disabled by default → operator must explicitly opt in
2. SAP API-policy evidence gate → tools with an UNKNOWN API surface are refused in strict mode
3. Plan validation + provider preflight (Databricks-first; Snowflake readiness-only)
4. **Dry-run required** → returns a correlation_id
5. Real execute must replay that correlation_id **and** pass a constant-time-compared approval token
6. Every outcome — block, dry-run, real, error — writes a redacted, sha256-hashed JSONL audit event

Safe-by-default isn't a slogan here; it's six independent gates, each defaulting to "closed."

Other design choices worth calling out:
• **Provider-neutral adapter** (`BDCConnectProvider`) so Databricks / Snowflake / future backends share one plan shape
• **Subprocess plugin upstreams** — `npx:` / `uvx:` / `cmd:` MCP servers proxied through the *same* audit + policy chain, distrusted by default
• Redaction covers signed Delta-share URLs, JWTs, and approval tokens before anything hits a log

The rails shipped first, on purpose — the first real provider mutation wiring lands in v0.3.

Repo + changelog in the comments.

P.S. The same governance layer — audit, policy, redaction, the gated interceptor — also powers my SAP Datasphere MCP server, released separately a few days ago.

#MCP #AgenticAI #SAP #BusinessDataCloud #Databricks #EnterpriseArchitecture #AItooling

---

## Draft 3 — Short + punchy (max reach)

Most "AI agent" demos skip the boring part: what happens when the agent actually *writes* to your system of record?

**SAP BDC MCP v0.2.0** is basically that boring part, done properly.

→ 25 governed tools for SAP Business Data Cloud
→ Writes off by default
→ Dry-run + approval token + audit log before anything mutates
→ Databricks-first, Snowflake-ready
→ `pip install` or `npx`

Governed SAP data ↔ agentic AI. Capability built *into* the guardrails, not around them.

Link below. 👇

(Same principle as my SAP Datasphere MCP server, shipped separately last week — read-only, same safe-by-default DNA.)

#SAP #MCP #AgenticAI #BusinessDataCloud

---

## Draft 4 — Narrative / thought-leadership ("why I built this")

For a year I've had the same conversation on repeat: leaders want AI agents to *act* on SAP data, and their security teams want to know exactly what the agent can touch, when, and with whose approval.

Both are right. The gap between them is where I've been building — and this week it has a shape you can install.

**SAP BDC MCP v0.2.0 — "Governed BDC Connect."** An MCP server that lets agents discover data products, validate contracts, and — now — execute shares against SAP Business Data Cloud. The word doing the heavy lifting is *governed*: writes are off until you enable them, high-risk actions must dry-run first, real execution needs a constant-time-compared approval token, and every call lands in an audit log with hashed, redacted inputs. Databricks is the first provider; Snowflake ships readiness-only; the first real mutation wiring is v0.3. The rails come before the train.

The pattern I keep returning to: **governance is the product.** Not a compliance checkbox at the end — the thing that makes agentic access to enterprise systems defensible in the first place. Build the gate chain, the audit trail, and the safe defaults first. Add capability into that frame, never around it.

If you're wiring agents into SAP, I'd genuinely like to compare notes.

Repo + changelog in the comments.

P.S. This is the same principle behind my SAP Datasphere MCP server, which I announced separately a few days back — read-only, same governed foundation.

#AgenticAI #SAP #EnterpriseAI #DataGovernance #MCP #BusinessDataCloud #SolutionArchitecture

---

## Draft 5 — Changelog "what shipped" update

📦 Shipped: **sap-bdc-mcp v0.2.0 — "Governed BDC Connect."**

The first execution-capable release — from contract-first discovery to a governed-execution server.

Added:
• Tool risk metadata on every tool (mutability / risk / API surface / evidence)
• SAP API-policy evidence gate — refuses UNKNOWN-surface mutators in strict mode
• JSONL audit log (sha256-hashed, redacted inputs) — tail via `bdc_audit_tail`
• Provider-neutral adapter — Databricks (first provider) + Snowflake (readiness-only)
• `bdc_share_execute_plan` — full dry-run → approval-token → audited-execute gate chain
• Subprocess plugin upstreams (`npx:` / `uvx:` / `cmd:`) through the same policy chain
• npx distribution wrapper — `npx -y sap-bdc-mcp@0.2.0`

Net: **25 tools** (12 + 13 new). Backward compatible with v0.1. Relicensed to **BSL 1.1** (auto-converts to Apache 2.0 in 2029).

Deferred next (v0.3 / roadmap): real Databricks + Snowflake mutation, HTTP transport, JWT approval tokens.

Changelog linked in the comments.

P.S. My SAP Datasphere MCP server — announced separately a few days ago — follows the same governed, safe-by-default principle.

#SAP #MCP #AgenticAI #BusinessDataCloud #Databricks #ModelContextProtocol

---

### Posting notes
- **Links go in the first comment**, not the body — LinkedIn suppresses reach on posts with outbound links in the body.
- Suggested comment: repo → github.com/rahulsethi/SAPBDCMCP · changelog → the CHANGELOG.md v0.2.0 section.
- Best length for reach: Drafts 1, 4, 5 are "see more" length (good dwell time); Draft 3 is a skim-stopper.
- Keep **Draft 2** as a follow-up technical post a few days after the main announcement, not the lead.
- The Datasphere line is intentionally a single closing sentence in each draft — a nod, not a co-announcement (it was announced on its own earlier).
