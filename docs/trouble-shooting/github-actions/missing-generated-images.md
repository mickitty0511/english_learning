# GitHub Actions - Generated Images Missing from Commits

## Issue
- Vocabulary automation pipeline completes successfully, but card images (for example `src/<word>/*.jpg`) do not appear in the pull request or `main`.
- Only `reports/layout_scores/<word>.csv` shows up in the diff.

## Root Cause & How It Was Identified
- `.gitignore` contained the pattern `out/`, which ignores every `out` directory anywhere in the repository.
- Running `git status` and `git ls-files --others --ignored --exclude-standard | grep src/out` showed that `src/out/` was ignored.
- Workflow logs (`gh run view <run-id> --log --job <job-id>`) included `saved: src/out/...` lines, confirming the images were generated but not staged.

## Resolution
- Update `.gitignore` so that only the root-level `out/` directory is ignored, while `src/out/` is explicitly tracked:
  ```gitignore
  /out/
  !src/out/
  !src/out/.meta/
  ```
- Optionally create a dummy file under `src/out/`, run `git status` to confirm that it is tracked, then remove the file.
- Re-run the workflow and verify that generated images are included in the PR.

## Related Files
- `.gitignore`
- `.github/workflows/_vocab_pipeline.yml`
