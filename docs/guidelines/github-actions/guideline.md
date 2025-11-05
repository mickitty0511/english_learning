# GitHub Actions Guidelines

Use this guide for troubleshooting and implementation involving GitHub Actions.

## Troubleshooting Process
1. Get the run ID of the workflow run.
2. Get the job ID of the job that failed.
3. Get the logs of the job.
4. Analyze the logs to identify the root cause. Reference the troubleshooting references below to help identify the relevant article.
5. Recommend solutions for the root cause.

## Implementation/Troubleshooting Knowledge
- [Generated Images Missing from Commits](../trouble-shooting/github-actions/missing-generated-images.md)
- [`format(...)` Expressions Trigger Syntax Errors](../trouble-shooting/github-actions/yaml-format-expression.md)
- [github-script Context Re-declaration](../trouble-shooting/github-actions/github-script-context-shadowing.md)

## Usage Notes
- After documenting a new incident, add the entry under docs/trouble-shooting/github-actions/ and link it here.