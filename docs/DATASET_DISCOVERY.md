# Dataset discovery

No dataset has been imported and no model has been trained.

## Candidates reviewed

| Dataset | Relevant contents | Access / license | Decision |
| --- | --- | --- | --- |
| MIMIC-IV-ED v2.2 | ED triage, vital signs, diagnoses, medication reconciliation, and patient tracking. | Credentialed PhysioNet access, required training, and dataset-specific data-use agreement under the PhysioNet Credentialed Health Data License. | Preferred research candidate, blocked until an authorized investigator obtains access. |
| CDC NHAMCS ED public-use files | National ED visit survey data and documentation. | Public-use files and technical documentation are available. | Candidate for exploratory analysis; target/acquity variable compatibility and feature mapping must be inspected before use. |

## Why no current model exists

The application needs a defensible three-level urgency target. Neither a label mapping nor metrics can be chosen without inspecting the selected data dictionary, class distribution, missingness, and clinical meaning. CURE therefore returns no ML prediction until that work is completed. Synthetic data, if ever used for engineering tests, will be labelled synthetic and never reported as clinical performance.

Sources: [MIMIC-IV-ED dataset page](https://physionet.org/content/mimic-iv-ed/2.2/), [MIMIC access requirements](https://mimic.mit.edu/docs/faq/how-to-get-access.html), and [CDC NHAMCS documentation](https://www.cdc.gov/nchs/nhamcs/documentation/index.html).
