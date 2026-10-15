# Governance framework

Instructions define policy; the PR checklist makes review explicit; dependency-free
Python gates check branch names, develop PR bases, PR sections, common assistant
phrases, commit format, private paths and common credential signatures. Optional
hooks check commits and Git-provided push destination refs and commit ranges.
Every pushed destination must be a semantic branch; protected destinations, tags
and branch deletions are blocked. New branches validate full ancestry; updates
validate the remote-to-local range, including detached or non-current commits.
Unknown remote objects fail closed until fetched. Secret signatures include
quoted JSON credential keys, with key boundaries to avoid unrelated suffix matches. CI independently checks PR event metadata,
commit range, index and all fetched reachable history. Event text is read from JSON
and never interpolated into shell commands. CI has read-only contents permission
and does not persist checkout credentials.

Diagnostics report paths and rules, never matching values. Signatures are bounded,
not exhaustive: inspect unknown credentials, private data and unfetched history.
Ignored untracked files are not scanned. Blockquoted examples are excluded from
prose checks; reviewers must inspect exclusions and language outside known patterns.
Review gate changes independently because a PR can modify its own checks. CI is
not mandatory branch protection; no repository security settings were changed.

No application framework is selected yet. Future application tests must prove
local conversion and no input transmission; governance tests make no such claim.
