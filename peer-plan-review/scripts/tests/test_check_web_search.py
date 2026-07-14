"""check_web_search.py diagnostic — env/registry parity with production runs."""

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, SCRIPTS_DIR)

import check_web_search
from _common.providers import OPENCODE_READ_ONLY_PERMISSION, PROVIDERS


class TestCheckWebSearchEnv(unittest.TestCase):
    def test_check_web_search_build_env_opencode_sets_deny_policy(self):
        """Regression: the diagnostic builds the opencode cmd with --auto, so
        the child env MUST carry the exact production deny policy — without it
        the probe runs opencode unsandboxed."""
        env = check_web_search.build_env("opencode")
        self.assertEqual(env["OPENCODE_PERMISSION"], OPENCODE_READ_ONLY_PERMISSION)

    def test_build_env_claude_disables_nonessential_traffic(self):
        env = check_web_search.build_env("claude")
        self.assertEqual(env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"], "1")

    def test_provider_names_track_registry(self):
        """PROVIDER_NAMES derives from PROVIDERS — a new provider in the
        registry flows into the diagnostic without a hand-edit."""
        self.assertEqual(check_web_search.PROVIDER_NAMES, list(PROVIDERS))


if __name__ == "__main__":
    unittest.main()
