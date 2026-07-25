#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deckmate_core import DeckMateCore


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        home = root / "home/deck"
        steamapps = home / ".local/share/Steam/steamapps"
        steamapps.mkdir(parents=True)
        (steamapps / "appmanifest_1091500.acf").write_text(
            '"AppState"\n{\n"appid" "1091500"\n"name" "Cyberpunk 2077"\n"installdir" "Cyberpunk 2077"\n}\n',
            encoding="utf-8",
        )

        core = DeckMateCore(str(root / "state"), str(home))
        print("STATUS")
        print(json.dumps(core.status(), indent=2))

        print("\nREQUEST: Set up FSR for Cyberpunk")
        plan = core.create_plan("Set up FSR for Cyberpunk")
        print(json.dumps(plan, indent=2))

        print("\nAPPROVE")
        operation = core.execute_plan(plan["id"])
        print(json.dumps(operation, indent=2))

        print("\nUNDO")
        rollback = core.rollback_last()
        print(json.dumps(rollback, indent=2))


if __name__ == "__main__":
    main()
