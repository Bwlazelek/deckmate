import asyncio
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class DeckyPluginAdapterTests(unittest.TestCase):
    def test_main_initializes_with_current_decky_directory_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_decky = types.SimpleNamespace(
                decky_SETTINGS_DIR=str(root / "settings"),
                DECKY_USER_HOME=str(root / "home/deck"),
                logger=FakeLogger(),
            )
            original = sys.modules.get("decky")
            original_main = sys.modules.pop("main", None)
            sys.modules["decky"] = fake_decky
            try:
                module = importlib.import_module("main")
                plugin = module.Plugin()
                asyncio.run(plugin._main())
                status = asyncio.run(plugin.get_status())
                self.assertTrue(status["ready"])
                self.assertEqual(status["mode"], "safe-local-poc")
                self.assertTrue((root / "settings/operations.json").exists())
                self.assertIn("DeckMate v0.1 started in safe non-root mode", fake_decky.logger.messages)
            finally:
                sys.modules.pop("main", None)
                if original_main is not None:
                    sys.modules["main"] = original_main
                if original is None:
                    sys.modules.pop("decky", None)
                else:
                    sys.modules["decky"] = original


if __name__ == "__main__":
    unittest.main()
