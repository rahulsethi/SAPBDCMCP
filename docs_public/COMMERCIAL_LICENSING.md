# Commercial Licensing — `sap-bdc-mcp`

`sap-bdc-mcp` is distributed under the [PolyForm Noncommercial License 1.0.0](../LICENSE). That license is free of charge for **noncommercial** use. **Commercial use requires a separate license** from the copyright holder.

This page explains what counts as commercial use, why a commercial license exists, and how to inquire about one.

---

## 1. Do I need a commercial license?

**You probably do NOT need a commercial license if:**

- You are an individual using `sap-bdc-mcp` for personal study, hobby projects, evaluation, or research that has no anticipated commercial application.
- You are a student or academic using it for coursework or unfunded / publicly-funded research.
- You work for a **charitable organization, educational institution, public research organization, public safety or health organization, environmental protection organization, or government institution** (the PolyForm Noncommercial license's "Noncommercial Organizations" carve-out — see [the LICENSE](../LICENSE) for the exact text).
- You are evaluating `sap-bdc-mcp` as part of a vendor selection process and have not yet committed it to production.

**You DO need a commercial license if:**

- You are a for-profit company using `sap-bdc-mcp` (or any derivative work of it) in production, in internal tooling that supports your commercial operations, or in a product or service you sell.
- You are embedding `sap-bdc-mcp` (in whole, in part, or as a derivative) in a product you distribute commercially.
- You are operating a managed service that depends on `sap-bdc-mcp` and offering it (paid or free) to third parties.
- You are using `sap-bdc-mcp` to deliver consulting services or SAP integration work to clients on a paid basis.

When in doubt, please ask. We will give you a clear answer in writing within a reasonable window.

## 2. Why a commercial license?

`sap-bdc-mcp` is built around a serious investment in safety, governance, and SAP-API-policy alignment. The author bears the cost of maintenance, security review, and SAP policy tracking on every release.

A commercial license is the mechanism that:

- Funds continued development.
- Aligns the project's roadmap with enterprise users' real needs (governance, audit, deployment patterns).
- Gives commercial users a clear, contractual relationship — including a defined channel for bug reports, security advisories, and roadmap input.

Charging only commercial users keeps the project freely usable for the people who would learn from it or use it noncommercially. We think that's the right trade-off.

## 3. What does a commercial license typically grant?

A typical commercial license for `sap-bdc-mcp` is negotiated based on:

- **Scope** — internal use by your organization vs. embedding in a product vs. operating a managed service vs. delivering it as part of consulting work.
- **Headcount or revenue** — small business, mid-market, enterprise tiers.
- **Term** — annual, multi-year, or perpetual.
- **Support** — basic (best-effort GitHub) vs. defined-SLA private channel vs. quarterly roadmap call.

What it grants:

- The right to use, modify, and embed `sap-bdc-mcp` within the agreed scope.
- A clear list of permitted internal redistributions.
- (Optional) Indemnification, warranty, and SLA terms.
- (Optional) A named point of contact and an obligation to respond to security advisories.

What it does **not** grant (unless specifically negotiated):

- The right to sublicense or re-sell `sap-bdc-mcp` as a standalone product.
- Trademark rights to the project name.
- The right to relicense under a different (e.g., open-source) license.

## 4. How to inquire

If you believe you need a commercial license:

1. Open a GitHub issue at <https://github.com/rahulsethi/SAPBDCMCP/issues> with the title `[licensing inquiry] <your-org>`.
2. Include the following so we can give you a useful answer quickly:
   - **Organization** — legal name, jurisdiction, approximate headcount or revenue band.
   - **Intended use** — internal tool, embedded in a product, managed service, consulting delivery, other.
   - **Scope** — single team / org-wide / customer-facing.
   - **Timeline** — when you need to be in production.
   - **Specific tools** — which `sap-bdc-mcp` tools you intend to enable (especially any `WRITE`-mutability or subprocess plugins).
   - **Contact** — preferred email and / or scheduling link.
3. Mark the issue private if your platform supports it, or DM the maintainer; if neither is convenient, posting a *non-confidential* version of the request publicly is fine — we will move sensitive details to a private channel once contact is established.

We will typically respond within a few business days with one of:

- A quote and proposed terms.
- A request for additional information.
- A statement that your intended use already qualifies as noncommercial and no separate license is needed.

## 5. Pricing

We do not publish a fixed price list. Pricing is negotiated per agreement, factoring scope, scale, and support tier. Honest estimates are typically in the range a mid-market SaaS subscription would occupy — meaningfully cheaper than building or maintaining a comparable governed-MCP layer in-house, and structured to be predictable for procurement.

## 6. Other questions

- **"My company is exploring `sap-bdc-mcp` and not yet in production — do I need a license now?"**  No. The PolyForm Noncommercial license permits evaluation. Once you commit it to commercial use, you will need a license at that point.
- **"We are a SAP partner / consultancy. Does the noncommercial license cover client work?"**  No. Paid consulting work that uses `sap-bdc-mcp` is commercial use. Please inquire about a partner license.
- **"Can I contribute back to the project?"**  Yes. Contributions are welcome under the contributor-license terms in `CONTRIBUTING.md`. Contributing does not require a commercial license. The maintainer reserves the right to relicense the project's own code base; your contribution is still credited and remains useful to noncommercial users in perpetuity.
- **"What about v0.1.0 — that was MIT?"**  Correct. Code already in use under the MIT-licensed v0.1.0 release stays under MIT for that version. The PolyForm Noncommercial license applies from v0.2.0 onward.

## 7. Quick links

- [`LICENSE`](../LICENSE) — the full PolyForm Noncommercial 1.0.0 text.
- [`INSTALLATION.md`](INSTALLATION.md) — how to install and configure the server.
- [`SAP_API_POLICY.md`](SAP_API_POLICY.md) — how `sap-bdc-mcp` aligns with SAP's API policy (often part of an enterprise procurement review).
- [`../CHANGELOG.md`](../CHANGELOG.md) — version history.
- GitHub Issues: <https://github.com/rahulsethi/SAPBDCMCP/issues>.
