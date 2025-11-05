# GitHub Actions — Generated Images Missing from Commits

## Issue
- Vocabulary automation pipeline finishes successfully, yet no card images (e.g., `src/<word>/*.jpg`) appear in the pull request or the `main` branch.
- Only `reports/layout_scores/<word>.csv` shows up in the diff.

## Root Cause & How It Was Identified
- `.gitignore` contained the pattern `out/`, which ignores *any* directory named `out` across the repository.  
- Running `git status` and `git ls-files --others --ignored --exclude-standard | grep src/out` confirmed that `src/out/` was being ignored.
- The workflow logs (`gh run view <run-id> --log --job <job-id>`) showed messages such as `saved: src/out/1_example.jpg`, proving that image generation itself succeeded.

## Resolution
- Update `.gitignore` so that it lists the generated images explicitly:
  ```gitignore
  !src/out/*.jpg
  !src/out/.meta/*.json
  ```

## Related Files
- `.gitignore`
- `.github/workflows/_vocab_pipeline.yml` (for context on where images are generated and staged)