# Project Guide

## Overview
- Purpose: register and study English words and collocations by logging them as GitHub issues and pairing each sense with supporting imagery.
- Tracking cadence: manage learning progress with weekly milestones that always span Monday through Sunday.

## Repository Layout
- `.github/ISSUE_TEMPLATE/WORD.md`: issue template for registering new vocabulary.
- `src/<word-or-collocation>/`: folder that stores reference images for each meaning (numbered to match the issue content).
- `AGENT.md`: this guide for the AI assistant.

## Word Registration Workflow
1. Confirm the weekly milestone exists (see Milestones section). If not, create it before opening the issue.
2. In GitHub Issues, click **New issue** and choose the `WORD` template.
3. Fill in:
   - Title with the word or collocation.
   - Meanings and example sentences, aligning numbering with stored images.
   - Attach the current weekly milestone.
4. Create or update the corresponding folder under `src/` (e.g., `src/might-want-to/`).
5. Store images named or grouped by meaning numbers (e.g., `1-<description>.jpg`, `2-<description>.jpg`). Ensure the numbering matches the issue.

## Image Management
- Keep one folder per word/collocation.
- For each meaning defined in the issue, place the images that illustrate that meaning in a subfolder or name them with the meaning number.
- If new images are added later, update the issue to reflect the additional resources.

## Milestones
- Define weekly milestones using the format `MM/DD/YYYY~MM/DD/YYYY`, where the range covers Monday through Sunday.
- Example for the current week (Tuesday, October 21, 2025 belongs to this range): `10/20/2025~10/26/2025`.
- Before creating a milestone, check existing milestones to avoid duplicates.
- When registering a word issue, assign it to the milestone covering the week of creation.

## Weekly Routine
- **Start of week (Monday):** ensure the new weekly milestone is created and note any carry-over issues.
- **Daily:** add new vocabulary issues via the template, upload corresponding images, and link them to the current milestone.
- **End of week (Sunday):** review milestone completion, move unfinished items to the next week, and archive notes.
