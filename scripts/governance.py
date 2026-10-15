"""Dependency-free repository governance. Diagnostics never print matching values."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TYPES = "feat|fix|chore|docs|refactor|test|perf|build"
PROVIDERS = {"codex", "claude", "openai", "anthropic", "gemini", "copilot", "agent", "agents", "chatgpt"}
CONVERSATION = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:hi(?:\s+there)?[!,]|hello[!,]|dear\s+user\b|"
    r"(?:i|we)(?:'ve| have| just)?\s+(?:completed|finished|implemented|updated|created)\s+(?:your|the requested)\b|"
    r"(?:as\s+you\s+requested|per\s+your\s+request)\b|"
    r"(?:let me know|would you like me|happy to help|hope this helps)\b|"
    r"here(?:'s| is)\s+(?:your|the requested)\b|"
    r"(?:thanks|thank you)\s+for\s+(?:your|the)\b)"
)

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def branch_errors(branch):
    if not re.fullmatch(rf"(?:{TYPES})/[a-z][a-z0-9]*(?:-[a-z0-9]+)+", branch):
        return ["branch: require type/descriptive-kebab-case"]
    if PROVIDERS.intersection(branch.split("/", 1)[1].split("-")):
        return ["branch: provider or agent identifiers are prohibited"]
    return []

def prose_errors(text):
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return ["prose: conversational assistant language"] if CONVERSATION.search(text) else []

def commit_errors(message):
    subject = message.splitlines()[0] if message.strip() else ""
    errors = prose_errors(message)
    if len(subject) > 100 or not re.fullmatch(rf"(?:{TYPES})(?:\([a-z0-9-]+\))?: \S.+", subject):
        errors.append("commit: require concise type: technical summary (maximum 100 characters)")
    errors += prose_errors(re.sub(r"^[^:]+:\s*", "", subject))
    return errors

def pr_errors(branch, base, title, body):
    errors = branch_errors(branch)
    if base != "develop":
        errors.append("base: ordinary pull requests must target develop")
    errors += prose_errors(title + "\n" + body)
    for heading in ("Summary", "Validation"):
        match = re.search(rf"(?ms)^## {heading}\s*\n(.*?)(?=^## |\Z)", body)
        if not match or not re.sub(r"<!--.*?-->", "", match[1], flags=re.S).strip(" \n\r-*"):
            errors.append("body: require substantive " + heading + " section")
    return errors

def private_path(name):
    parts = PurePosixPath(name.lower()).parts
    base = parts[-1]
    return (any(p in {".aws", ".codex", ".claude", "private", "local-files", "production", "exports", "creds"} for p in parts)
            or base == ".env" or base.startswith(".env.") and base != ".env.example"
            or base.endswith((".pem", ".key", ".p12", ".pfx", ".tfstate"))
            or bool(re.match(r"(?:credentials|secrets).*\.json$", base)))

SECRET_RULES = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "aws-access-key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "assigned-secret": re.compile(rb"(?im)(?<![A-Za-z0-9_-])(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)[\"']?\s*[=:]\s*[\"']?([A-Za-z0-9/+_=.-]{20,})"),
}

def content_rules(data):
    return [rule for rule, pattern in SECRET_RULES.items() if pattern.search(data)]

def scan(revisions=()):
    errors = []
    versions = [("index", item) for item in git("ls-files", "-z").decode().split("\0") if item]
    for commit in git("rev-list", "--all", *revisions).decode().splitlines():
        versions += [(commit, item) for item in git("ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0") if item]
    seen = set()
    for revision, name in versions:
        if private_path(name):
            errors.append(f"private-file: {name} ({revision[:12]})")
        spec = f":{name}" if revision == "index" else f"{revision}:{name}"
        data = git("show", spec)
        key = (name, data)
        if key not in seen:
            seen.add(key)
            errors += [f"secret/{rule}: {name} ({revision[:12]})" for rule in content_rules(data)]
    return sorted(set(errors))

def pre_push_errors(updates):
    """Validate Git's actual pushed refs, including non-current and detached heads."""
    errors = []
    commits = set()
    for line in updates.splitlines():
        fields = line.split()
        if len(fields) != 4:
            errors.append("push: malformed ref update")
            continue
        local_ref, local_oid, remote_ref, remote_oid = fields
        if not all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid) for oid in (local_oid, remote_oid)):
            errors.append("push: malformed object identifier")
            continue
        if not remote_ref.startswith("refs/heads/"):
            errors.append("push: only semantic branch destinations are allowed")
        else:
            errors += branch_errors(remote_ref.removeprefix("refs/heads/"))
        if set(local_oid) == {"0"}:
            errors.append("push: branch deletion requires a separate authorized maintenance operation")
            continue
        revision = local_oid if set(remote_oid) == {"0"} else f"{remote_oid}..{local_oid}"
        try:
            commits.update(git("rev-list", revision).decode().splitlines())
        except subprocess.CalledProcessError:
            errors.append("push: cannot inspect commit range; fetch the destination before retrying")
    for sha in sorted(commits):
        errors += [f"{sha[:12]}: {error}" for error in commit_errors(git("show", "-s", "--format=%B", sha).decode())]
    errors += scan(tuple(sorted(commits)))
    return errors


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--branch", required=True)
    check.add_argument("--base", required=True)
    check.add_argument("--title", default="Repository policy update")
    check.add_argument("--body-file", type=Path, required=True)
    sub.add_parser("scan")
    sub.add_parser("ci")
    sub.add_parser("pre-push")
    commit = sub.add_parser("commit")
    commit.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "check":
        errors = pr_errors(args.branch, args.base, args.title, args.body_file.read_text(encoding="utf-8"))
    elif args.command == "commit":
        errors = branch_errors(git("branch", "--show-current").decode().strip()) + commit_errors(args.file.read_text(encoding="utf-8"))
    elif args.command == "scan":
        errors = scan()
    elif args.command == "pre-push":
        errors = pre_push_errors(sys.stdin.read())
    else:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pr = event["pull_request"]
        errors = pr_errors(pr["head"]["ref"], pr["base"]["ref"], pr["title"], pr.get("body") or "")
        for sha in git("rev-list", f'{pr["base"]["sha"]}..{pr["head"]["sha"]}').decode().splitlines():
            errors += [f"{sha[:12]}: {error}" for error in commit_errors(git("show", "-s", "--format=%B", sha).decode())]
        errors += scan()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Governance checks passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
