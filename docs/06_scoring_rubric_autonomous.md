
# Scoring & Merge Rubric — Autonomous System

## SCORING AXES (1–5)

Impact: correctness, robustness, clarity
Risk: likelihood of regression
Effort: cognitive + implementation cost

## FORMULA

Priority = (Impact × Confidence) − (Risk + Effort)

## MERGE THRESHOLDS

- Priority < 3 → Reject
- Risk ≥ 4 → Reject unless critical bug
- Effort > Impact → Reject

This rubric is binding.
