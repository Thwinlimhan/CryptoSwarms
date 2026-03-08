# AutoResearch Program

This file controls nightly autoresearch behavior.

## Policy
- max_runtime_minutes: 20
- max_experiments: 3
- generations_per_experiment: 6
- mutation_step: 0.05
- min_score_improvement: 0.02
- keep_top_k: 1

## Promotion rule
Only promote candidates that beat incumbent score by at least `min_score_improvement`.
Discard all others.
