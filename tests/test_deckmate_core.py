import json
import tempfile
import unittest
from pathlib import Path

from deckmate_core import DeckMateCore, DeckMateError


class DeckMateCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home = root / "home" / "deck"
        self.state = root / "state"
        steamapps = self.home / ".local/share/Steam/steamapps"
        steamapps.mkdir(parents=True)
        (steamapps / "appmanifest_1091500.acf").write_text(
            '"AppState"\n{\n  "appid" "1091500"\n  "name" "Cyberpunk 2077"\n  "installdir" "Cyberpunk 2077"\n}\n',
            encoding="utf-8",
        )
        self.core = DeckMateCore(str(self.state), str(self.home))

    def tearDown(self):
        self.temp.cleanup()

    def test_discovers_steam_game(self):
        games = self.core.scan_games()
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["appid"], "1091500")
        self.assertEqual(games[0]["name"], "Cyberpunk 2077")

    def test_graphics_request_creates_approval_plan(self):
        plan = self.core.create_plan("Set up FSR for Cyberpunk")
        self.assertEqual(plan["topic"], "graphics")
        self.assertEqual(plan["status"], "awaiting_approval")
        self.assertEqual([item["type"] for item in plan["actions"]], ["scan_games", "record_recommendation"])

    def test_execute_then_rollback(self):
        plan = self.core.create_plan("Install GE-Proton for Cyberpunk")
        operation = self.core.execute_plan(plan["id"])
        self.assertEqual(operation["status"], "completed")
        receipt = Path(operation["created_files"][0])
        self.assertTrue(receipt.exists())
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertIn("no game or system files", payload["notice"])

        rollback = self.core.rollback_last()
        self.assertEqual(rollback["status"], "rolled_back")
        self.assertFalse(receipt.exists())

    def test_rejects_duplicate_execution(self):
        plan = self.core.create_plan("Set up emulation")
        self.core.execute_plan(plan["id"])
        with self.assertRaises(DeckMateError):
            self.core.execute_plan(plan["id"])

    def test_rejects_empty_and_oversized_requests(self):
        with self.assertRaises(DeckMateError):
            self.core.create_plan("  ")
        with self.assertRaises(DeckMateError):
            self.core.create_plan("x" * 1001)

    def test_cancel_prevents_execution(self):
        plan = self.core.create_plan("Install a mod")
        cancelled = self.core.cancel_plan(plan["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        with self.assertRaises(DeckMateError):
            self.core.execute_plan(plan["id"])


if __name__ == "__main__":
    unittest.main()
