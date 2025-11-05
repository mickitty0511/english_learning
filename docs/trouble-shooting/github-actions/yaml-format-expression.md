# GitHub Actions - `format(...)` Expressions Trigger Syntax Errors

## Issue
- Expressions such as `format('Vocab: {0}', steps.parsed.outputs.word_display)` triggered syntax errors in IDE validation or `actionlint`.

## Root Cause & How It Was Identified
- Some tooling mis-handles GitHub Actions `format()` when positional placeholders (`{0}`) are used.
- The reusable workflow `_vocab_pipeline.yml` relied on these expressions, and lint runs failed consistently.

## Resolution
- Move string assembly logic into the composite action `./.github/actions/derive-strings`.
- Reference outputs like `steps.strings.outputs.pr_title` instead of calling `format()` inline. This eliminates the warning.

## Related Files
- `.github/actions/derive-strings/action.yml`
- `.github/workflows/_vocab_pipeline.yml`
