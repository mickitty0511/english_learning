# GitHub Actions - `github-script` Context Re-declaration

## Issue
- Steps using `actions/github-script@v7` re-declared `const context = github.context;` (and sometimes `const core = require('@actions/core')`), leading to runtime errors such as `Identifier 'core' has already been declared` or `Cannot read properties of undefined (reading 'repo')`.

## Root Cause & How It Was Identified
- `github-script` injects `core`, `github`, and `context` automatically; redeclaring them shadows the provided bindings.
- Workflow logs showed stack traces originating from `github-script` complaining about duplicate identifiers.

## Resolution
- Remove the redundant declarations and reference `github.context` (or the provided `context` object) directly.
- Re-run the workflow to confirm the absence of duplicate identifier errors.

## Related Files
- `.github/actions/comment-structured/action.yml`
- `.github/actions/comment-legibility/action.yml`
