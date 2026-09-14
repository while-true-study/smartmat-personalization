# public_release_v1 — model-ready smart-mat windows

**Status: release candidate. External publication is pending: a data license and a hosting/DOI decision are
required first (see `docs/P7_PUBLIC_RELEASE_CHECKLIST.md`).**

## Purpose

This package contains the minimum data needed to reproduce the main results of this repository's study under frozen
protocol v1.0. The study estimates temperature and humidity from multi-channel smart-mat pressure, with strict
leave-one-subject-out evaluation and chronological personalization:
- strict leave-one-subject-out baselines (P3);
- feature-family comparison (P4);
- chronological personalization (P5);
- night-level robustness analysis (P6).

It is a derived product. It contains no raw log file, no canonical row table and no participant metadata.

## Cohort

- **Three anonymous subjects:** `User01`, `User02`, `User07`.
- **Four recording streams:**
  - `User01|unknown` and `User07|unknown`;
  - `User02|22480` and `User02|22482`: two mats of the same person, recorded concurrently, always one subject.
- **Device IDs** are mat hardware IDs (`unknown` where the source carries none). They identify equipment, not
  people.
- The subjects were never recorded at the same time. Subject, period, season, device and microclimate are therefore
  confounded, and results describe an unseen subject under that combined shift.

## Files

| File | Content |
|---|---|
| `windows.parquet` | one row per model-ready window: identifiers, relative times, 8 × 6 raw pressure values, targets, validity flags, window-set membership |
| `splits/v1.0_loso/outer_folds.csv`, `splits/v1.0_loso/inner_folds.csv` | leave-one-subject-out outer folds and the two-way inner splits (per session) |
| `splits/v1.0_personalization/chronological.csv` | chronological personalization split (per session × night and budget) |
| `control_events.csv` | User02 heater on/off control codes (`AHON`/`AHOF`) with relative times, used only for descriptive strata; never a model input |
| `p5_plan_public.yaml` | the frozen personalization plan with relative night keys |
| `reference_digests.json` | SHA-256 of the frozen prediction values, for bitwise reproduction checks |
| `schema.json` | column types, units, ranges and roles |
| `excluded_sources.csv` | sources that are not part of this release, with the reason and the decision |
| `manifest.json` | versions, counts, the temporal method and the SHA-256 of every file |

The column-level documentation is in `docs/P7_PUBLIC_DATA_DICTIONARY.md` in the code repository.

## Anonymization and time

- **Only anonymous subject IDs are used.** There are no names, initials, folder names, messenger IDs, file names or
  paths, and no participant metadata.
- **No calendar date appears anywhere.** For each subject, time is counted in seconds from local midnight of the day
  of the subject's first recorded night:
  - `*_time_s` columns hold these seconds;
  - nights are keyed `D####`, the relative day of the night (noon to noon);
  - readable times are written `D#### HH:MM:SS`;
  - `night_ordinal` numbers the recorded nights 1…N.
- **Order, gaps, clock time of day and night grouping are exact.** Calendar dates, weekdays and the calendar
  alignment between subjects are removed.

## Windows, inputs and targets

- **Window rule:** 40-s windows of 8 bins × 5 s, stride 20 s. Each bin holds the last observed row, gaps are at most
  5 s, and windows never cross a session, device or phase boundary.
  - Windows with `in_loso = true` form the leave-one-subject-out set.
  - Windows with `in_rq2 = true` are additionally cut at night boundaries and form the personalization set. Most
    windows are in both.
- **Model input:** the six pressure channels at the eight steps (`s{step}_p{channel}`, raw ADC counts 0–4095),
  divided by 4095 by the models; 4095 is kept.
- **Targets:** temperature (°C) and relative humidity (%RH) at the last step. A window is labelled only if both
  validity flags are true.
- **Nothing else** (no time, identity, phase or control field) is a model input.

## Excluded material

Not released:
- one source confirmed invalid by the data provider;
- two quarantined files with unresolved device attribution;
- restricted participant metadata;
- two auxiliary legacy sources that the frozen protocol does not use.

They are listed in `excluded_sources.csv` without any of their data.

## Reproduction

With the code repository checked out at the release commit and this package in `data/release/public_release_v1/`:

```
python scripts/validate_public_release.py --data data/release/public_release_v1
python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier core
python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier extended
```

- `core` re-trains the frozen P3 models, re-runs the P5 personalization and the P6 analysis.
- `extended` also re-trains the frozen P4 feature-family models.
- Both compare everything with the committed results.
- Neither re-runs the hyperparameter searches.
- The environment and expected run times are listed in the repository README.

## Limitations

- Three subjects only; no population-level inference.
- The targets are measured inside a heater-controlled mat microclimate.
- The release reproduces the frozen protocol v1.0 analyses. It is not a general-purpose sleep or occupancy dataset.

## Citation and license

- **Citation:** to be added with the publication.
- **License:** not yet decided. A license decision is required before external publication.
