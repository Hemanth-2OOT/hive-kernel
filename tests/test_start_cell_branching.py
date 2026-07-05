"""
Unit tests for Reservoir._start_cell_unsafe command-building logic.

These tests assert the exact `cmd` passed to subprocess.Popen for each cell type,
without spawning real processes. This covers the if/elif/else branching that was
silently corrupted during a previous edit (mangled elif → plain if, dropped raise
ValueError) and caught only by manual diff-review rather than by a failing test.

Having this test mechanically catches the same class of regression going forward.
"""
import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch, call
from hive.config import HiveConfig
from hive.runtime.reservoir import Reservoir


def _make_mock_proc(boot_msg=None, ready_msg=None):
    """Return a mock Popen object whose stdout yields a boot then ready message."""
    proc = MagicMock()
    proc.poll.return_value = None  # process is alive
    boot = boot_msg or json.dumps({"status": "booting"})
    ready = ready_msg or json.dumps({"status": "ready"})
    proc.stdout.readline.side_effect = [boot + "\n", ready + "\n"]
    return proc


class TestStartCellUnsafeCmdBranching(unittest.TestCase):
    """
    Assert the exact cmd list built for each cell type.
    Nothing is actually spawned — subprocess.Popen is fully mocked.
    """

    def setUp(self):
        self.config = HiveConfig()
        # Prevent Popen from spawning anything real across all tests
        self.popen_patcher = patch("hive.runtime.reservoir.subprocess.Popen")
        self.mock_popen = self.popen_patcher.start()

        # Prevent _ensure_capacity_unsafe from doing real VRAM arithmetic
        self.capacity_patcher = patch.object(
            Reservoir, "_ensure_capacity_unsafe", return_value=None
        )
        self.capacity_patcher.start()

        self.res = Reservoir(self.config)

    def tearDown(self):
        self.popen_patcher.stop()
        self.capacity_patcher.stop()

    def _spawn(self, cell_type):
        """Call _start_cell_unsafe and return the cmd that was passed to Popen."""
        self.mock_popen.return_value = _make_mock_proc()
        self.res._start_cell_unsafe(cell_type)
        self.assertTrue(self.mock_popen.called, "Popen was not called")
        return self.mock_popen.call_args[0][0]  # first positional arg = cmd list

    # -------------------------------------------------------------------------
    # LLM cells — must carry keep_alive_sec as argv[2]
    # -------------------------------------------------------------------------

    def test_qwen_cmd_includes_keep_alive(self):
        cmd = self._spawn("qwen2.5-coder:7b")
        self.assertEqual(cmd[2], "qwen2.5-coder:7b", "argv[1] must be cell_type")
        self.assertEqual(
            cmd[3], str(self.config.ollama_keep_alive_sec),
            "argv[2] must be ollama_keep_alive_sec for LLM cells"
        )
        self.assertIn("llm_server.py", cmd[1], "script must be llm_server.py")

    def test_hermes_cmd_includes_keep_alive(self):
        cmd = self._spawn("hermes3:8b")
        self.assertEqual(cmd[2], "hermes3:8b")
        self.assertEqual(cmd[3], str(self.config.ollama_keep_alive_sec))
        self.assertIn("llm_server.py", cmd[1])

    def test_generic_llm_cmd_includes_keep_alive(self):
        cmd = self._spawn("llm")
        self.assertEqual(cmd[2], "llm")
        self.assertEqual(cmd[3], str(self.config.ollama_keep_alive_sec))
        self.assertIn("llm_server.py", cmd[1])

    # -------------------------------------------------------------------------
    # Non-LLM cells — must NOT carry keep_alive_sec (3-arg cmd only)
    # -------------------------------------------------------------------------

    def test_embedding_cmd_no_keep_alive(self):
        cmd = self._spawn("embedding")
        self.assertEqual(len(cmd), 3, "embedding cmd must have exactly 3 args")
        self.assertEqual(cmd[2], "embedding")
        self.assertIn("embedding_server.py", cmd[1])

    def test_sentiment_cmd_no_keep_alive(self):
        cmd = self._spawn("sentiment")
        self.assertEqual(len(cmd), 3, "sentiment cmd must have exactly 3 args")
        self.assertEqual(cmd[2], "sentiment")
        self.assertIn("sentiment_server.py", cmd[1])

    # -------------------------------------------------------------------------
    # Unknown cell type — must raise immediately, not silently build a broken cmd
    # -------------------------------------------------------------------------

    def test_unknown_cell_type_raises(self):
        with self.assertRaises(ValueError):
            self.res._start_cell_unsafe("unknown_model_xyz")
        self.mock_popen.assert_not_called()

    # -------------------------------------------------------------------------
    # keep_alive_sec value is an int on the wire, not a quoted string
    # (argv is string, but the value must round-trip correctly through int())
    # -------------------------------------------------------------------------

    def test_keep_alive_argv_is_valid_int_string(self):
        cmd = self._spawn("qwen2.5-coder:7b")
        argv2 = cmd[3]
        self.assertIsInstance(argv2, str, "argv must be a str (subprocess requirement)")
        self.assertEqual(
            int(argv2), self.config.ollama_keep_alive_sec,
            "argv[2] must round-trip through int() to the configured value"
        )

    # -------------------------------------------------------------------------
    # Config change propagates to cmd without touching llm_server.py
    # -------------------------------------------------------------------------

    def test_custom_keep_alive_sec_propagates(self):
        """Changing HiveConfig.ollama_keep_alive_sec must flow through to cmd."""
        self.config.ollama_keep_alive_sec = 120
        cmd = self._spawn("qwen2.5-coder:7b")
        self.assertEqual(cmd[3], "120")


if __name__ == "__main__":
    unittest.main(verbosity=2)
