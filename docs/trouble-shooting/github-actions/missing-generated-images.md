# GitHub Actions — Generated Images Missing from Commits

## Issue
- Vocabulary automation pipeline finishes successfully, yet no card images (e.g., `src/<word>/*.jpg`) appear in the pull request or the `main` branch.
- Only `reports/layout_scores/<word>.csv` shows up in the diff.

## Root Cause & How It Was Identified
- `.gitignore` contained the pattern `out/`, which ignores *any* directory named `out` across the repository.  
- Running `git status` and `git ls-files --others --ignored --exclude-standard | grep src/out` confirmed that `src/out/` was being ignored.
- The workflow logs (`gh run view <run-id> --log --job <job-id>`) showed messages such as `saved: src/out/1_example.jpg`, proving that image generation itself succeeded.

## Resolution
- Update `.gitignore` so that it re-allows the `src/out/` directory and explicitly tracks generated assets and metadata:
  ```gitignore
  out/
  !src/out/
  !src/out/.meta/
  ```
- (Optional sanity check) Locally create dummy files under `src/out/` and run `git status` to ensure they appear; delete the temporary files afterward.
- Re-run the vocabulary pipeline workflow and confirm that generated images now show up in the PR diff.

## Related Files
- `.gitignore`
- `.github/workflows/_vocab_pipeline.yml` (for context on where images are generated and staged)
