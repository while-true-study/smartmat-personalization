"""Build paper/manuscript/manuscript_p14_revision.md from manuscript_p13_revision.md by exact, checked replacements.

  python scripts/export_p13_tables.py && python scripts/render_p14_figures.py \
      && python scripts/build_p14_manuscript_revision.py && python scripts/render_p14_revision.py \
      && python scripts/validate_p14_revision.py

manuscript.md, manuscript_p10_revision.md and manuscript_p13_revision.md are read only. No result number changes: the
P14 revision withdraws Figure S5, writes the Option A data-availability draft (D-070), rewrites the Table 11 caption
(arrow, User02 footnote, paired night-cluster bootstrap) and states the scope of the post-hoc heater diagnostic.
Every replacement target must occur exactly once. Decisions: D-069, D-070.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402

SRC = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p13_revision.md"
DST = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p14_revision.md"
t = SRC.read_text(encoding="utf-8").replace("\r\n", "\n")
ETA = ".3f"


def t11(s, col, spec=".2f"):
    return "{{" + f"p13_table11_heater | subject_id={s} | {col} | {spec}" + "}}"


R = []

# ---------------------------------------------------------------- header comment
R.append(("""<!--
P13 REVISION: a revised copy of paper/manuscript/manuscript_p10_revision.md, built by
scripts/build_p13_manuscript_revision.py; manuscript.md and manuscript_p10_revision.md are kept unchanged. Changes are
listed in paper/manuscript/REVISION_P13_NOTES.md. New numbers are tokens resolved from paper/tables/p11_*.csv,
p12_*.csv and p13_*.csv (scripts/export_p13_tables.py). Figure 6 and Figure S5 are drawn by
scripts/render_p13_figures.py into paper/manuscript/revision_p13/figures/; Tables S35-S44 are in
paper/manuscript/revision_p13/supplementary/. Render: scripts/render_p13_revision.py; checks:
scripts/validate_p13_revision.py.""",
"""<!--
P14 SUBMISSION CANDIDATE (D-069, D-070): a revised copy of paper/manuscript/manuscript_p13_revision.md, built by
scripts/build_p14_manuscript_revision.py; manuscript.md, manuscript_p10_revision.md and manuscript_p13_revision.md are
kept unchanged. No result number differs from P13. Changes are listed in paper/manuscript/REVISION_P14_NOTES.md.
Figure 6 is drawn by scripts/render_p14_figures.py into paper/manuscript/revision_p14/figures/; Tables S35-S44 are in
paper/manuscript/revision_p13/supplementary/. Render: scripts/render_p14_revision.py; checks:
scripts/validate_p14_revision.py. Metadata blockers: docs/P14_SUBMISSION_METADATA_CHECKLIST.md.
P13 REVISION: numbers are tokens resolved from paper/tables/p11_*.csv, p12_*.csv and p13_*.csv
(scripts/export_p13_tables.py)."""))

# ---------------------------------------------------------------- Methods 3.5.9: scope of the post-hoc diagnostic
R.append(("""  causal heater exposure, and the conditioned constant is not an admissible estimator.
""",
"""  causal heater exposure, and the conditioned constant is not an admissible estimator.
- **Scope:** the diagnostic was not used for model selection; no heater or controller field was added to the inputs
  of the RAW-TCN, the boosted or the ridge models; and no window length, history length or baseline rule was changed
  after its results were seen.
"""))

# ---------------------------------------------------------------- Results 4.11: Table 11 caption, table and footnote
start = "**Table 11.** Heater-context diagnostic (post hoc, descriptive), temperature."
end = "\n\n- **Association:** for User01 and User07"
i0, i1 = t.index(start), t.index(end)
if t.count(start) != 1 or t.count(end) != 1:
    raise SystemExit("Table 11 block boundaries are not unique")


def row11(s, share_spec):
    cells = [s, f"{t11(s, 'on_windows_full', ',d')} ({t11(s, 'on_share_pct_full', share_spec)} %)",
             f"{t11(s, 'eta_raw_full', ETA)} → {t11(s, 'eta_night_centred_full', ETA)}",
             t11(s, "mae_source_mean_common"), t11(s, "mae_source_median_common"),
             t11(s, "mae_heater_conditioned_common"),
             f"{t11(s, 'delta_mae', '+.2f')} [{t11(s, 'ci_lower', '+.2f')}, {t11(s, 'ci_upper', '+.2f')}]",
             t11(s, "mae_hgb_900_common")]
    return "| " + " | ".join(cells) + " |"


table11 = "\n".join(
    ["| Subject | Heater-on windows (share) | η² (raw → within night) | Source mean | Source median | "
     "Heater-conditioned source constant | ΔMAE [95 % CI] | Boosting 900 s |",
     "|" + "---|" * 8, row11("User01", ".1f"), row11("User02", ".2f"), row11("User07", ".1f")])

new_t11 = f"""**Table 11.** Heater-context diagnostic (post hoc, descriptive), temperature. Heater-on windows: labelled windows
within 60 min after a heater-on code, with their share of all labelled windows of the held-out subject (all nights).
η²: the share of the observed temperature variance associated with the three heater contexts (all nights), to three
decimals; η² values are shown as raw-target η² → within-night-centred η². MAE (°C) on the common endpoints of
Table 10: the source-training mean and median, the heater-conditioned source constant and boosting at 900 s.
ΔMAE = MAE(source mean) − MAE(heater-conditioned source constant). Confidence intervals were obtained by the
pre-specified paired night-cluster bootstrap: whole test nights were resampled together with all their windows
(2,000 resamples, 95 % percentile intervals); windows were not resampled individually. The heater-conditioned source
constant is a diagnostic comparator, not an admissible pressure-only estimator: it uses controller codes that may
depend on the measured temperature, and it mixes heater context with the composition of the source subjects.

{table11}

For User02, η² after additional within-night × mat centring was
{t11('User02', 'eta_night_x_mat_centred_full', ETA)}; this sensitivity analysis uses a different nuisance adjustment
from the primary within-night value. User02 had heater-on context in only {t11('User02', 'on_windows_full', ',d')}
windows, so inference about its heater-on state is very limited."""
R.append((t[i0:i1], new_t11))

# ---------------------------------------------------------------- Supplementary list: Figure S5 withdrawn
R.append(("""the adaptation budget b: (a) temperature, (b) humidity; Figure S5: One example night per held-out subject, selected by
a fixed rule, with total pressure, temperature, humidity and heater on/off codes over relative time; Table S1:""",
"""the adaptation budget b: (a) temperature, (b) humidity; Table S1:"""))

# ---------------------------------------------------------------- Data Availability: Option A draft (D-070)
R.append(("""(Section 3.5.7) are not part of the release candidate. The exploratory analyses of Sections 3.5.8–3.5.9 use the
canonical dataset; the heater-context diagnostic needs heater codes that the release candidate contains for one
subject only.""",
"""(Section 3.5.7) are not part of the release candidate. The exploratory analyses of Sections 3.5.8–3.5.9 use the
canonical dataset.

<!-- D-070, Option A: draft wording within the currently authorised scope. It is not final: no request-based access
is offered, because no data-provider permission for it is on record. -->
The controller-event records used in the post-hoc heater-context diagnostic (Section 3.5.9) are not included in the
public release because their redistribution has not been authorized; the release candidate contains the heater codes
of one subject only. Aggregate diagnostic results and the analysis code may be included in the research release,
subject to final author and data-provider approval [PI AND DATA-PROVIDER DECISION: inclusion of the aggregate
heater-diagnostic results and analysis code — CONFIRM]. The public release therefore does not independently reproduce
the heater-context diagnostic from the underlying controller-event records."""))

text = t
for old, new in R:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"replacement target found {n} times: {old[:90]!r}")
    text = text.replace(old, new)
write_text(DST, text)
print(f"wrote {DST.relative_to(paths.PROJECT_ROOT)} with {len(R)} replacements")
