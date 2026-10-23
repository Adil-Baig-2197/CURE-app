# Dataset discovery

The CDC NHAMCS 2022 ED public-use SAS file has been downloaded into the ignored `data/nhamcs/` directory and extracted for local inspection/training. The source archive and raw microdata are intentionally excluded from version control. The evaluation ran on all 16,025 source records. `IMMEDR` had 10,207 visits with levels 1–5 and 5,818 excluded records: 364 blank (`-9`), 3,788 unknown (`-8`), 587 reporting no triage (`0`), and 1,079 at facilities that do not conduct nursing triage (`7`). Among known target records, class counts were: level 1: 139 (1.36%); level 2: 1,595 (15.63%); level 3: 5,340 (52.32%); level 4: 2,826 (27.69%); level 5: 307 (3.01%).

## Candidate review

| Candidate | Relevant fields and target | Access and usage | Fit and limitations |
| --- | --- | --- | --- |
| CDC 2022 NHAMCS Emergency Department Public Use File | 16,025 visit records in the codebook. `IMMEDR` is the unimputed, provider-recorded triage level: 1 immediate, 2 emergent, 3 urgent, 4 semi-urgent, 5 nonurgent. Other potential intake-time fields include `AGE`, `TEMPF`, `PULSE`, `RESPR`, `BPSYS`, `BPDIAS`, `POPCT`, `PAINSCALE`, and reason-for-visit codes `RFV1`–`RFV5`. | CDC publishes public-use files and SAS/Stata readers. Raw data are not redistributed in this repository. Check current NCHS terms before external redistribution or publication. | Useful for an exploratory proxy task because it records triage labels, but this is prediction of provider behavior, not true need or outcomes. The sampled U.S. ED visit context, complex sample design, and incomplete fit to CURE's symptom/history inputs limit transfer. 2022 was the final NHAMCS collection year. |
| MIMIC-IV-ED v2.2 | About 425,000 ED stays; triage table includes acuity 1–5, vital signs, pain, and chief complaint. Other tables include medications and diagnoses. | Credentialed PhysioNet access, CITI training, and a dataset-specific data-use agreement under the PhysioNet Credentialed Health Data License 1.5.0. | Richer ED record, but access is restricted. Diagnoses and later medication/treatment data could leak post-triage information and must be excluded from an intake-time model. One hospital's triage practice may not generalize. |

## Exploratory target and feature plan

The first evaluation uses the original five `IMMEDR` levels without collapsing them. Values `-9` (blank), `-8` (unknown), `0` (no triage for a visit at an ESA that does triage), and `7` (facility does not conduct nursing triage) are excluded from supervised targets and reported separately. This avoids inventing a three-class urgency mapping without a clinician. The pipeline uses age, initial vitals, pain scale, and five visit-reason codes as features, and excludes post-triage diagnoses, orders, treatment, disposition, hospital identifiers, and survey design identifiers. `PATWT` is used as training sample weight and for weighted metrics; this does not substitute for a full complex-survey model evaluation.

## Remaining validation and release work

1. The codebook-aligned data audit and exploratory training are complete: target distribution and unknown/no-triage codes are reported above and detailed feature missingness is in the evaluation JSON.
2. Confirm the data and model artifact use terms before external redistribution; raw data are kept out of Git.
3. Evaluate the domain gap between an ED visit survey and CURE's patient-completed intake use case.
4. Document the point-in-time feature set and the limitations of weighting and random train/validation/test splits.
5. Obtain clinician review before interpreting the results or using them in a workflow.

## Exploratory model comparison

Two models were trained with a stratified 70/15/15 train/validation/test split (seed 42/43). Both were refit on train plus validation before the final held-out test. `PATWT` was used for fitting and survey-weighted metrics. The model chosen provisionally on validation weighted macro-F1 was logistic regression: validation 0.315 versus random forest 0.226. On the held-out test, logistic regression weighted macro-F1 was **0.358** (unweighted 0.343; weighted balanced accuracy 0.361); random forest weighted macro-F1 was **0.233** (unweighted 0.225; weighted balanced accuracy 0.254). The logistic model's unweighted recall was only 0.190 for level 1 (4/21 test records) and 0.109 for level 5 (5/46), so the headline score hides serious errors on rare classes. Random forest recall was zero for level 1 and 5 and 0.008 for level 2. Neither candidate is suitable for CURE use.

These are exploratory estimates against historical staff triage labels. They do not establish clinical safety or benefit. The test split is not temporal, external, or a full complex-survey evaluation; the class-1 test support is only 21. No subgroup fairness analysis, calibration assessment, prospective validation, or clinician review has been completed. The chosen validation candidate is only a research comparison; neither artifact is integrated into CURE.

The reproducible training environment and comparison pipeline live in `ml/`; local joblib artifacts and metrics are excluded from Git. The detailed metrics, per-class precision/recall/F1, confusion matrices, split counts, versions, and feature missingness are in `ml/artifacts/evaluation.json`. A model trained on historical provider-assigned triage predicts those labels, not a diagnosis or proof of patient outcomes.

## Sources

- [CDC NHAMCS public-use files and documentation](https://www.cdc.gov/nchs/nhamcs/documentation/index.html)
- [2022 NHAMCS ED micro-data documentation](https://ftp.cdc.gov/pub/health_statistics/nchs/dataset_documentation/NHAMCS/doc22-ed-508.pdf)
- [NHAMCS 2022 ED sample record](https://www.cdc.gov/nchs/data/nhamcs/2022-NHAMCS-ED-PRF-sample-card-508.pdf)
- [MIMIC-IV-ED v2.2](https://physionet.org/content/mimic-iv-ed/2.2/)
- [NHAMCS survey overview and final collection year](https://www.cdc.gov/nchs/nhamcs/about/index.html)
