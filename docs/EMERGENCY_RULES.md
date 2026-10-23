# Emergency-warning rules

CURE's emergency warning is a conservative, rule-based routing layer independent of ML. It is not a diagnosis, is incomplete, and requires clinical review before production use. A positive flag tells the patient to seek emergency help immediately and never to wait for the application, triage queue, or clinician response.

Current prototype triggers are severe breathing difficulty, emergency chest-pain patterns, sudden FAST-type stroke symptoms, and unresponsiveness. They are based on NHS public guidance: [chest pain](https://www.nhs.uk/symptoms/chest-pain/), [shortness of breath](https://www.nhs.uk/symptoms/shortness-of-breath/), and [stroke symptoms](https://www.nhs.uk/conditions/stroke/symptoms/). The wording and rule coverage require clinician approval.
