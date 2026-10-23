# Emergency-warning rules

CURE's emergency warning is a conservative, rule-based routing layer independent of ML. It is not a diagnosis, is incomplete, and requires clinical review before production use. A positive flag tells the patient to seek emergency help immediately and never to wait for the application, triage queue, or clinician response.

Current prototype triggers are severe breathing difficulty, blue/grey/unusually pale lips or skin, emergency chest-pain patterns, sudden FAST-type stroke symptoms, sudden confusion, and unresponsiveness. They are based on NHS public emergency guidance for [chest pain](https://www.nhs.uk/symptoms/chest-pain/), [shortness of breath](https://www.nhs.uk/symptoms/shortness-of-breath/), and [stroke symptoms](https://www.nhs.uk/conditions/stroke/symptoms/). NHS guidance supports asking about these warning signs; it does not validate this CURE rule implementation, which may miss emergencies and must be clinically reviewed and tested in context before any real-world use.

CURE does not show a country-specific phone number. The patient message directs people to seek local emergency help immediately. A positive warning takes precedence over model output, and an absent warning must never be interpreted as evidence that the patient is safe.
