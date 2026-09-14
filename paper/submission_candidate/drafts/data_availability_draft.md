# Data Availability Statement — draft

> **Status: draft. External availability is pending**, and nothing below may be changed to "publicly available" until
> each bracketed item is resolved (P7 checklist D1–D3; docs/P8_MANUSCRIPT_PLAN.md §9).
> - Placeholders stay as written: `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]`.
> - No value is invented.

## Draft text (current state)

> The raw sensor recordings analysed in this study are not publicly released: public releases are built as a
> separate, derived and de-identified subset (DATA_POLICY §5.4), and restricted participant metadata is never
> released.
>
> A de-identified, model-ready derived dataset, `public_release_v1`, has been prepared as a release candidate. It
> contains the model-ready windows of three anonymous participants (four mat streams), the evaluation splits and the
> reference digests needed to reproduce the results reported here. Time is given only relative to each participant's
> first recorded night; no calendar date is included.
>
> External availability of this dataset is pending the choice of a data license, a repository with a persistent
> identifier, and final approval. Until then, the data are available from the corresponding author on reasonable
> request [PI DECISION: confirm or replace this sentence].
>
> Data repository: [DATA REPOSITORY]. DOI: [DOI]. License: [LICENSE].

## Text for the final version, after the blockers are resolved

> The de-identified, model-ready dataset supporting this study (`public_release_v1`) is openly available in
> [DATA REPOSITORY] at [DOI] under [LICENSE].
>
> It contains 575,265 model-ready 40-s windows from three anonymous participants (four mat streams): raw pressure
> values, temperature and humidity targets with validity flags, and relative night and time identifiers. It also
> includes the leave-one-subject-out and chronological personalization splits, a data dictionary and a manifest with
> SHA-256 checksums.
>
> Raw recordings and participant metadata are not released.

## Facts the statement may rely on (P7)

- Content: see `docs/P7_PUBLIC_DATA_DICTIONARY.md` and the package README.
- Manifest SHA-256 `72ac8cf347696d929b4408e3e1b21895cfe18b80a0d748188b47311c43f0f70f`; `windows.parquet`
  29,955,714 bytes.
- Exclusions: provider-confirmed invalid source, quarantined files, restricted metadata, auxiliary legacy sources.
- Relative time only (D-049). `windows.parquet` is not in the Git repository (D-050).

## Open items

| Item | Owner | Reference |
|---|---|---|
| Data license | PI | P7 checklist D1 |
| Repository and DOI | PI | P7 checklist D2 |
| Approval of the release subset and final release | PI | P7 checklist D3, D-051 |
| Whether "available on request" is offered in the interim, and by whom | PI | — |
