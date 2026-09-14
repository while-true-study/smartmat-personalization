# P8 — Final blockers before submission and `v1.0-paper`

> **State at the end of the P8 final integration pass** (branch `paper/p8-manuscript`).
> - The scientific text is integrated. The items below are still open, and none is presented as resolved in the
>   manuscript: each appears there as a bracketed placeholder.
> - Nothing here changes a frozen result. `v1.0-paper` is not created, and P8 is not merged, until every gate in §4
>   holds.

## 1. Submission and publication metadata

| # | Item | State | Owner | Manuscript placeholder | Blocks | Tracking |
|---|---|---|---|---|---|---|
| 1 | Exact Applied Sciences instructions (section structure, Featured Application, abstract/keywords, reference style, prior publication, extended conference papers, cover letter, template version, limits) | open: mdpi.com returns 403 to automated access; only the Word template was read directly | authors (browser check) | section structure as drafted; Featured Application standalone | formatting; submission | `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` items 1–5, 15–20 |
| 2 | Conference final bibliography: proceedings volume, pages, DOI, URL | open | PI | `note` field of `maeng2026icfice` in `references.bib` | reference list; cover letter | OPEN-27 |
| 3 | Conference copyright holder, and whether any permission is needed (none expected: no text, table or figure is reused) | open | PI | `[PENDING]` / `[VERIFY]` in the disclosure draft | cover letter | OPEN-27; `CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md` |
| 4 | Funding statement (the conference statement is not copied) | open | PI | `[FUNDING TO BE CONFIRMED BY PI]` | Funding; Conflicts of Interest | manuscript back matter |
| 5 | Ethics / IRB information | open | PI | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | IRB statement | OPEN-26 |
| 6 | Informed consent wording. The provider's consent confirmation (D-002) is not an ethics approval and is not the statement itself | open | PI | `[INFORMED CONSENT WORDING REQUIRED FROM PI]` | Informed Consent Statement | OPEN-26 |
| 7 | GenAI tool/version inventory and approval of the disclosure | partly done: repository sessions inventoried (§2); tools used outside them and PI approval pending | PI + authors | `[OTHER GENERATIVE-AI TOOLS, IF ANY: …]` in the Acknowledgments; §3.8 text for approval | Materials and Methods §3.8; Acknowledgments | OPEN-28; D-052 |
| 8 | Code license | open; the repository has no LICENSE file | PI | `[LICENSE]` | Code Availability; external release | OPEN-22 |
| 9 | Data license of `public_release_v1` | open | PI | `[LICENSE]` | Data Availability; external release | OPEN-22 |
| 10 | Hosting of `public_release_v1` | open | PI | `[DATA REPOSITORY]`, `[CODE REPOSITORY]` | Data/Code Availability | OPEN-23 |
| 11 | DOI (data; code archive) | open | PI | `[DOI]` | Data/Code Availability | OPEN-23 |
| 12 | PI approval of the release subset and of the final manuscript/release state | open | PI | — | `v1.0-paper`; external release | OPEN-24 |
| 13 | Public scope of the calendar dates in committed repository files outside the release package | open | PI | — | any public repository or code archive | OPEN-25 |
| 14 | Author list, affiliations, corresponding author, CRediT roles | open | PI | `[AUTHORS AND AFFILIATIONS — PI]`; `[CONFIRM]` in `AUTHOR_CONTRIBUTIONS_DRAFT.md` | first page; Author Contributions | — |
| 15 | Conflicts of interest; other acknowledgments | open | PI | `[PI]`, `[OTHER ACKNOWLEDGMENTS — PI]` | back matter | — |
| 16 | Final title and keyword list | recommendation made; PI decides | PI | `[TITLE — PI DECISION …]`, `[FINAL LIST: PI]` | first page | `docs/P8_TITLE_CANDIDATES.md` |
| 17 | Interim data access ("on reasonable request", and from whom) | open | PI | `[PI DECISION: …]` in the Data Availability Statement | Data Availability | `DATA_AVAILABILITY_DRAFT.md` |

## 2. Generative-AI tool inventory (OPEN-28)

**Evidence:**
- The local Claude Code session logs of this project: two sessions, every assistant message recorded with its model
  identifier and client version.
- The repository and its Git history: no other AI tool is named. `AGENTS.md` and `CLAUDE.md` are tool-neutral entry
  points (D-001). By convention, commits carry no AI attribution (CONVENTIONS §6.6).
- Nothing is inferred beyond these sources.

| Product | Provider | Model / version | Evidence | Purpose |
|---|---|---|---|---|
| Claude Code (command-line client) | Anthropic | client versions 2.1.263 and 2.1.270; model Claude Opus 5, identifier `claude-opus-5` (no other model appears in the logs) | local session logs of this repository | code drafting and debugging; organization and orchestration of the analysis workflow (running pipelines, tests and checks); research documentation (reports, decisions); literature screening and reference-metadata checks against Crossref and DOI records; manuscript drafting; language refinement |
| Any other generative-AI tool used by the authors outside these sessions (e.g. for planning, translation or language editing) | [TO BE CONFIRMED BY AUTHORS] | [VERSION TO BE CONFIRMED] | none in the repository | [TO BE CONFIRMED BY AUTHORS] |

**Controls that apply to every AI-assisted output** (stated in §3.8):
- The authors set the protocol, the dataset policies, the model-selection rules, the statistics and the
  interpretation boundaries. These are frozen in `docs/`, and the decision log records who decided.
- Executable results passed automated tests, the frozen-result checks, deterministic table generation and a
  clean-checkout reproduction (P7).
- Manuscript numbers are source tokens resolved from the frozen tables.
- Every retained reference was checked against its DOI or publisher record.

## 3. Production items (formatting stage; no new result)

| Item | State |
|---|---|
| Manuscript table export (`scripts/export_manuscript_tables.py`, planned): Tables 1–5 and S-tables from the frozen CSVs, night ids as ordinals | not built. The captions and column content are fixed in the manuscript and `docs/P8_TABLE_FIGURE_SELECTION.md` |
| Figures 2–4 and S1–S4 re-rendered from the committed figure data without the report titles | not done. The committed report figures stay unchanged |
| Figure 1 drawn from `paper/manuscript/FIGURE1_SCHEMATIC.md` | specification done; drawing pending |
| Manuscript validator (`scripts/validate_manuscript_results.py`, planned) | not built. The scratch checks of this pass (tokens, citations, privacy, claims) are recorded in `docs/P8_CITATION_AUDIT.md` §Final audit |
| Reference list rendered in MDPI numbered style from `references.bib` | pending (style: requirements item 5) |
| Supplementary file assembly (S1–S19, Figures S1–S4) | pending |

## 4. Gates to `v1.0-paper`

- Every item in §1 is resolved, or deliberately stated as open in the submitted text with PI approval.
- The production items in §3 are done, and the rendered manuscript passes the manuscript validator. No rendered number
  may differ from its frozen cell.
- The privacy review holds: no calendar date, no private source label, no restricted metadata, no local path.
- The frozen P3–P7 artifacts are unchanged against `p7-release-candidate`.
- PI approval (OPEN-24).
