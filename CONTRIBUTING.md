# Contributing to Csvify

## Workflow

Preserve existing files and history. Fetch origin, start ordinary work from fresh
`origin/develop`, and use an isolated semantic branch such as
`feat/local-csv-conversion` or `chore/repository-governance`. Allowed types are
feat, fix, chore, docs, refactor, test, perf and build. Use lowercase kebab-case
with at least two descriptive words; provider names (including codex, claude,
openai, anthropic, gemini, copilot and agent) are not branch prefixes or slugs.
Never commit ordinary work directly to main or develop.

Normal PRs target develop. Create drafts with an explicit base:
`gh pr create --draft --base develop --head YOUR_BRANCH`.
Before sharing the link, read `gh pr view NUMBER --json baseRefName,headRefName,headRefOid`
and verify develop, the intended branch and exact commit. Review the actual diff
and CI results. Main is for explicitly authorized release promotions. A release
or recovery requires a separately approved policy change; normal gates do not
silently exempt main. Do not merge, deploy, alter DNS, create credentials or
change repository security settings without explicit scope authorization.

Commit subjects use `type: technical summary` (optional scope); bodies and PRs
are concise technical repository artifacts: problem, change, validation and
material limits. Never address the user, narrate the chat, claim permission,
or add assistant sign-offs. Specific technical uses of words such as user,
request and you in quoted documentation are not inherently conversational.

## Architecture and public repository

Conversion and user data stay entirely in the client. Do not add application
credentials, server processing, input uploads, telemetry containing input, or
external data transmission without explicit scope approval. Future application
tests must prove local conversion works with networking disabled and assert
input is never sent through fetch, XHR, WebSocket, beacon or form submissions.
Governance checks do not prove application behavior; no application tests exist yet.

Do not commit environment files, private keys, credential stores, production
configuration, private customer data or local exports. Defensive scanning catches
accidental unrelated credential leakage. Review every staged file and all new
history before push. Never print suspected secret values; report rule and path.
If a credential is found, stop publication and arrange revocation outside this PR.

## Validation and review

Run `python -m unittest discover -s tests -v` and
`python scripts/governance.py check --branch YOUR_BRANCH --base develop --body-file PR_BODY_FILE`.
Run `python scripts/governance.py scan` for tracked files and reachable history.
Install optional local hooks with `git config core.hooksPath .githooks`.
Hooks are convenience gates, CI is independent; neither replaces review.

Review checklist: semantic branch; fresh develop ancestry; actual PR base/head;
concise technical commit and PR text; scoped diff; passing positive and negative
gate tests; tracked-file and history scan; no private files or input transmission;
accurate validation claims. Gate changes require inspection of the gate itself.
CI checks can be bypassed unless maintainers separately require them; this setup
does not change repository security settings.

## Bootstrap exception

On 2026-10-15 the local path was absent and `git ls-remote` returned no refs.
A governance-document baseline was committed on main, then develop was created
at the identical commit. This is the sole empty-repository exception to normal
feature flow. Executable gates and tests are developed on
`chore/repository-governance` and submitted to develop; no application code or
release is part of bootstrap. Neighboring Oordia governance supplies the branch
policy; shared VCS bootstrap was not run because its staging/tracker mutations
exceed this scope.
