# Third-party licences

Gatekeeper's own code is MIT (see [LICENSE](../LICENSE)). This page lists what the project uses, under which licence, and what I actually checked. It is not legal advice.

**How to read the "Checked" column.** *Read on 24 Nov 2026* means I read the licence or the vendor's licence page that day. *Known, not re-read* means I know the licence from experience but did not re-read it for this page. *Not confirmed* means I could not read the source and you should not rely on my entry.

## What is shipped and what is only used

- **Shipped by this repo:** my own code, my container image (`ghcr.io/nisha1805/gatekeeper-compliance`) with its Python packages, and a copy of EU legal texts.
- **Only used, not shipped:** LiteLLM, Argo CD, kind, Kyverno, Prometheus, Grafana, Terraform, Docker Desktop and the others are downloaded by whoever runs the Quick start. Nothing from them is copied into this repo.

## Legal texts

| Material | Terms | Checked |
| --- | --- | --- |
| EU AI Act (Regulation (EU) 2024/1689) and amendment (Regulation (EU) 2026/1744), copied into `app/compliance/data/ai_act.json` | The Commission's legal notice says EU-owned content is licensed under CC BY 4.0: reuse is allowed with credit and a note of any changes. Source: EUR-Lex, https://eur-lex.europa.eu. Changes made here: split into single provisions, formatting removed, added text marked. Only the Official Journal text is authentic. | Commission legal notice read on 24 Nov 2026. EUR-Lex's own legal notice did **not** load for me: please read its copyright section yourself. |

## Infrastructure and tools (used, not shipped)

| Tool | Licence | Checked |
| --- | --- | --- |
| LiteLLM | MIT, except the `enterprise/` directory, which has its own licence. I use virtual keys, budgets, routing and fallback, and nothing from the enterprise tier. | Read on 24 Nov 2026 (LICENSE file). That I use no enterprise feature is my own reading of the config. |
| Terraform | Business Source License 1.1. HashiCorp says non-production use is permitted and internal use is not restricted, and that products not sold or supported on a paid basis are allowed. | Vendor FAQ read on 24 Nov 2026. It does not name portfolio projects, so this is my reading. |
| Grafana | AGPL-3.0 (since 2021). Grafana Labs says unmodified distributions are not affected. I run it unmodified through a community Helm chart. | Vendor statement read on 24 Nov 2026. |
| Docker Desktop | Free for personal use, education, non-commercial open source, and companies with fewer than 250 employees and under 10 million USD revenue. Larger companies need a paid subscription. | Read on 24 Nov 2026. |
| tehcyx/kind Terraform provider | Not confirmed | Not confirmed: check the LICENSE file on the project's GitHub page before you list it. |
| Argo CD, kind, Helm, Kyverno, Prometheus | Apache-2.0 | Known, not re-read |
| PostgreSQL | PostgreSQL Licence | Known, not re-read |
| pytest, gitleaks | MIT | Known, not re-read |

## Python packages in the container image (shipped)

| Package | Licence | Checked |
| --- | --- | --- |
| FastAPI, pydantic | MIT | Known, not re-read |
| uvicorn, starlette, httpx | BSD-3-Clause | Known, not re-read |
| psycopg (with psycopg-binary) | LGPL-3.0 | Known, not re-read. It is used unmodified as a library, and each package's licence file stays inside the image. |
| Streamlit (test interface, not in the image) | Apache-2.0 | Known, not re-read |

## Open points

- The exact licences of the transitive Python packages are not listed one by one. A licence scan of the image would close this.
- The Anthropic API is used under Anthropic's own terms. No Anthropic software is copied into the repo.
- The project name is also used by the unrelated Open Policy Agent "Gatekeeper" for Kubernetes. This project is not related to it.
