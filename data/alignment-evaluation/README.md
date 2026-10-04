# Cross-role alignment regression set

Twelve authored synthetic cases cover mobile development, analytics, machine learning, design, security, and business tools. Each role contains three required skills; labels distinguish supported mentions from learning, negation, and embedded near-matches. Expected matches are stored separately from the runtime catalog and never enter comparison requests.

Run `python scripts/evaluate_alignment.py` from the repository root. It reports per-case predictions, false positives/negatives, aggregate precision, and recall. The committed cases contain 25 positive matches and 11 non-matches.

This is a regression set, not independently labeled real candidate data or a held-out accuracy benchmark. Do not use its results to claim universal accuracy. Live OpenAI semantic proposals need separate evaluation with authorized API credentials and reviewed relevance labels.
