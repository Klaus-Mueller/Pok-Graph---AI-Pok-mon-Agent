# Recorded examples

Read-only snapshot of the main catalog queries against a populated graph.

| File | Contents |
| --- | --- |
| [`parameters.json`](parameters.json) | IDs chosen after coverage checks. HeartGold/SoulSilver (`version_id` 15/16, `version_group_id` 10) plus `red-blue` as a second group. |
| [`expected-results.json`](expected-results.json) | Rows returned with those parameters, plus a dataset fingerprint. |
| [`plans.md`](plans.md) | `EXPLAIN` trees. No extra indexes were added. |

Refresh:

```bash
PYTHONPATH=src python -m tests.integration.record_examples
```
