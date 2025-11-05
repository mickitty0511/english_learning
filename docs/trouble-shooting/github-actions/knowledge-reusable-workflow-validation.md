# Reusable Workflow Validation Run on Push

- **Context:** Commit `9851b09bf86f2fa31f0f9c23c802c0550b2f3855` introduced `.github/workflows/_vocab_pipeline.yml` on 2025-11-05.
- **Observed Run:** GitHub Actions run 19090313180 (2025-11-05T03:28:14Z) started automatically right after the push with event `push` and concluded in `failure` with no jobs executed.
- **Root Cause:** Newly created workflows in `.github/workflows/` trigger a one-time validation run. Because `_vocab_pipeline.yml` is declared with `on: workflow_call`, GitHub cannot populate the required inputs during validation, so it skips job creation and marks the run as failed.
- **Impact:** The failure is expected and does not indicate an issue with the reusable workflow. Subsequent `workflow_call` invocations from `vocab_create.yml` / `vocab_edit.yml` operate normally.
- **Mitigation Options:**
  - Stage reusable workflows on a preparation branch until ready, then merge.
  - Place reusable workflows outside `.github/workflows/` (for example in `.github/workflows/reusable/`) and reference them via relative path once stable.
- **Verification Command:** `gh api repos/mickitty0511/english_learning/actions/runs/19090313180`
