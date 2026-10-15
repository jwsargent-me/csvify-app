# Csvify agent instructions

Read CONTRIBUTING.md before branch, commit or PR operations. It is the canonical
workflow, architecture and review policy for every tool and provider.

Keep all Csvify work in this repository. Preserve user work. Start from fresh
origin/develop on an isolated semantic branch without provider prefixes; normal
PRs explicitly target develop. Verify the actual remote base, head and commit
before sharing a draft PR. Write concise technical commits and PR descriptions,
never conversational messages to the user. Run the mechanical gates and inspect
the review checklist; do not claim checks that did not run.

Csvify is entirely client-side: user input stays local. No application secrets,
server processing or upload paths without explicit scope approval. No application
features, merges, deployment, DNS or repository security changes in governance work.
