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

if __name__ == "__main__":
    unittest.main()
