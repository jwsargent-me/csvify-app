import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("governance", Path(__file__).resolve().parents[1] / "scripts/governance.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
BODY = "## Summary\nValidate repository policy.\n\n## Validation\nPython policy tests pass.\n"

class GovernanceTests(unittest.TestCase):
    def test_semantic_branches(self):
        for name in ("chore/repository-governance", "feat/local-csv-conversion", "fix/user-input-parser"):
            self.assertEqual([], g.branch_errors(name))

    def test_invalid_branches(self):
        for name in ("main", "develop", "codex/setup", "agent/setup", "feat/codex-setup", "fix/bug", "chore/Bad-name", "feat/parser--update"):
            self.assertTrue(g.branch_errors(name), name)

    def test_bases(self):
        self.assertEqual([], g.pr_errors("chore/repository-governance", "develop", "Enforce repository policy", BODY))
        for base in ("main", "staging", ""):
            self.assertIn("base:", "\n".join(g.pr_errors("chore/repository-governance", base, "Policy checks", BODY)))

    def test_conversational_language(self):
        for phrase in ("Hi there!", "I've completed your request.", "As you requested, gates are ready.", "Let me know if you need changes.", "Would you like me to continue?", "Hope this helps!"):
            self.assertTrue(g.pr_errors("chore/repository-governance", "develop", "Policy checks", BODY + "\n" + phrase), phrase)

    def test_technical_prose_not_broad_keywords(self):
        for phrase in ("Reject user input uploads.", "Request parser handles empty CSV.", "You can run the local converter offline.", "Document the phrase 'let me know' as a rejected example.", "> Let me know if this helps."):
            self.assertEqual([], g.prose_errors(phrase))

    def test_sections(self):
        self.assertTrue(g.pr_errors("chore/repository-governance", "develop", "Policy", "## Summary\n<!-- placeholder -->\n## Validation\n"))

    def test_commits(self):
        self.assertEqual([], g.commit_errors("chore: enforce repository governance"))
        for message in ("Done", "fix: I've completed your request", "docs: update policy\n\nHope this helps!"):
            self.assertTrue(g.commit_errors(message))

    def test_private_paths(self):
        for name in (".env", ".env.production", "private/data.csv", ".aws/credentials", "config/key.pem", "credentials.json", "production/config.json"):
            self.assertTrue(g.private_path(name), name)
        for name in (".env.example", "docs/production-guide.md", "scripts/governance.py"):
            self.assertFalse(g.private_path(name), name)

    def test_secret_signatures(self):
        samples = [b"gh" + b"p_" + b"a" * 36, b"AK" + b"IA" + b"A" * 16,
                   b"-----BEGIN " + b"PRIVATE KEY-----", b"api_key=" + b"x" * 24]
        for sample in samples:
            self.assertTrue(g.content_rules(sample))
        self.assertEqual([], g.content_rules(b"api_key=EXAMPLE\npassword=<placeholder>"))

    def test_deleted_secret_in_history_and_sanitized_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.check_output(["git", "-C", folder, *args], stderr=subprocess.DEVNULL)
            git("init", "-b", "main")
            git("config", "user.name", "Policy Test")
            git("config", "user.email", "policy@example.invalid")
            secret = b"gh" + b"p_" + b"z" * 36
            (root / "leaked.txt").write_bytes(secret)
            git("add", ".")
            git("commit", "-m", "test: add synthetic fixture")
            git("rm", "leaked.txt")
            git("commit", "-m", "test: remove synthetic fixture")
            with patch.object(g, "ROOT", root):
                errors = g.scan()
            self.assertTrue(any("secret/github-token" in x for x in errors))
            self.assertNotIn(secret.decode(), "\n".join(errors))

    def test_quoted_secret_keys(self):
        for key in ("api_key", "client_secret", "password", "access_token"):
            for quote in ('"', "'"):
                value = b"q" * 24
                fixture = (quote + key + quote + ": " + quote).encode() + value + quote.encode()
                self.assertIn("assigned-secret", g.content_rules(fixture), key)
        for fixture in (b'{"api_key": "EXAMPLE"}', b'{"password": "<placeholder>"}',
                        b'{"not_password": "' + b"q" * 24 + b'"}'):
            self.assertEqual([], g.content_rules(fixture))

    def test_push_destinations_and_deletions(self):
        oid = "a" * 40
        zero = "0" * 40
        with patch.object(g, "scan", return_value=[]), patch.object(g, "git", return_value=b""):
            self.assertEqual([], g.pre_push_errors(f"HEAD {oid} refs/heads/fix/local-parser {zero}"))
            for destination in ("refs/heads/main", "refs/heads/develop", "refs/heads/codex/setup", "refs/tags/v1"):
                self.assertTrue(g.pre_push_errors(f"HEAD {oid} {destination} {zero}"), destination)
            # Mixed pushes must inspect every destination; the checked-out branch is irrelevant.
            self.assertTrue(g.pre_push_errors(f"HEAD {oid} refs/heads/fix/local-parser {zero}\nHEAD {oid} refs/heads/main {zero}"))
            for destination in ("refs/heads/main", "refs/heads/fix/local-parser"):
                self.assertTrue(g.pre_push_errors(f"(delete) {zero} {destination} {oid}"))
            self.assertTrue(g.pre_push_errors("malformed update"))

    def test_push_checks_actual_range(self):
        old, new = "a" * 40, "b" * 40
        def fake_git(*args):
            if args[0] == "rev-list":
                self.assertEqual(("rev-list", f"{old}..{new}"), args)
                return (new + "\n").encode()
            return b"I've completed your request\n"
        with patch.object(g, "git", side_effect=fake_git), patch.object(g, "scan", return_value=[]) as scan:
            self.assertTrue(g.pre_push_errors(f"refs/heads/other {new} refs/heads/fix/local-parser {old}"))
            scan.assert_called_once_with((new,))

    def test_new_push_checks_full_ancestry(self):
        new = "b" * 40
        with patch.object(g, "git", return_value=b"") as git, patch.object(g, "scan", return_value=[]):
            self.assertEqual([], g.pre_push_errors(f"HEAD {new} refs/heads/fix/local-parser {'0' * 40}"))
            git.assert_called_once_with("rev-list", new)

    def test_unknown_push_range_fails_closed(self):
        with patch.object(g, "git", side_effect=subprocess.CalledProcessError(128, "git")), patch.object(g, "scan", return_value=[]):
            errors = g.pre_push_errors(f"HEAD {'a' * 40} refs/heads/fix/local-parser {'b' * 40}")
            self.assertTrue(any("cannot inspect commit range" in error for error in errors))

    def test_push_scans_dangling_commit_and_json_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.check_output(["git", "-C", folder, *args], stderr=subprocess.DEVNULL)
            git("init", "-b", "chore/repository-governance")
            git("config", "user.name", "Policy Test")
            git("config", "user.email", "policy@example.invalid")
            git("commit", "--allow-empty", "-m", "test: establish fixture baseline")
            base = git("rev-parse", "HEAD").decode().strip()
            git("checkout", "--detach")
            secret = b"q" * 24
            (root / "config.json").write_bytes(b'{"api_key": "' + secret + b'"}')
            git("add", ".")
            git("commit", "-m", "test: add synthetic JSON fixture")
            git("rm", "config.json")
            git("commit", "-m", "Done")
            head = git("rev-parse", "HEAD").decode().strip()
            git("checkout", "chore/repository-governance")
            with patch.object(g, "ROOT", root):
                errors = g.pre_push_errors(f"HEAD {head} refs/heads/fix/local-parser {base}")
            self.assertTrue(any("commit:" in error for error in errors))
            self.assertTrue(any("secret/assigned-secret" in error for error in errors))
            self.assertNotIn(secret.decode(), "\n".join(errors))

if __name__ == "__main__":
    unittest.main()
