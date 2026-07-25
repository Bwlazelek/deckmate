"""Safe, dependency-free core for the DeckMate Decky plugin.

The core intentionally exposes typed actions rather than arbitrary shell execution.
It can be tested on any machine without Decky Loader installed.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class DeckMateError(RuntimeError):
    pass


class DeckMateCore:
    ALLOWED_ACTIONS = {"scan_games", "record_recommendation"}

    def __init__(self, state_dir: str, user_home: str):
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.user_home = Path(user_home).expanduser().resolve()
        self.plans_dir = self.state_dir / "plans"
        self.receipts_dir = self.state_dir / "receipts"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.journal_path = self.state_dir / "operations.json"
        if not self.journal_path.exists():
            self._write_json(self.journal_path, [])

    def status(self) -> Dict[str, Any]:
        games = self.scan_games()
        return {
            "ready": True,
            "mode": "safe-local-poc",
            "root_enabled": False,
            "arbitrary_shell_enabled": False,
            "game_count": len(games),
            "message": "DeckMate is ready. Every write requires plan approval and supports rollback.",
        }

    def create_plan(self, prompt: str) -> Dict[str, Any]:
        clean_prompt = " ".join(prompt.strip().split())
        if not clean_prompt:
            raise DeckMateError("Please enter a request.")
        if len(clean_prompt) > 1000:
            raise DeckMateError("Request is too long for the proof of concept.")

        lower = clean_prompt.lower()
        topic = self._classify(lower)
        actions: List[Dict[str, Any]] = [
            {
                "type": "scan_games",
                "label": "Inspect installed Steam games",
                "risk": "read-only",
                "description": "Read Steam app manifests under the deck user's home directory.",
            }
        ]
        if topic != "library":
            actions.append(
                {
                    "type": "record_recommendation",
                    "label": f"Create a {topic} setup receipt",
                    "risk": "low",
                    "description": "Write only to DeckMate's private settings directory as a reversible proof of execution.",
                    "topic": topic,
                    "request": clean_prompt,
                }
            )

        plan = {
            "id": uuid.uuid4().hex[:12],
            "created_at": int(time.time()),
            "status": "awaiting_approval",
            "title": self._title_for(topic),
            "summary": self._summary_for(topic, clean_prompt),
            "request": clean_prompt,
            "topic": topic,
            "risk": "read-only" if topic == "library" else "low",
            "actions": actions,
            "limitations": self._limitations_for(topic),
        }
        self._write_json(self._safe_child(self.plans_dir, f"{plan['id']}.json"), plan)
        return plan

    def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        plan = self._load_plan(plan_id)
        if plan.get("status") != "awaiting_approval":
            raise DeckMateError("This plan is no longer awaiting approval.")

        results: List[Dict[str, Any]] = []
        created_files: List[str] = []
        try:
            for action in plan.get("actions", []):
                action_type = action.get("type")
                if action_type not in self.ALLOWED_ACTIONS:
                    raise DeckMateError(f"Blocked unknown action: {action_type}")
                if action_type == "scan_games":
                    games = self.scan_games()
                    results.append({"type": action_type, "ok": True, "games": games})
                elif action_type == "record_recommendation":
                    receipt = {
                        "plan_id": plan["id"],
                        "created_at": int(time.time()),
                        "topic": action.get("topic"),
                        "request": action.get("request"),
                        "notice": "Proof-of-concept receipt only; no game or system files were changed.",
                    }
                    receipt_path = self._safe_child(self.receipts_dir, f"{plan['id']}.json")
                    self._write_json(receipt_path, receipt)
                    created_files.append(str(receipt_path))
                    results.append({"type": action_type, "ok": True, "receipt": str(receipt_path)})

            operation = {
                "id": uuid.uuid4().hex[:12],
                "plan_id": plan["id"],
                "created_at": int(time.time()),
                "status": "completed",
                "summary": plan["title"],
                "created_files": created_files,
                "results": results,
                "rollback_available": bool(created_files),
            }
            plan["status"] = "completed"
            plan["completed_at"] = int(time.time())
            self._write_json(self._safe_child(self.plans_dir, f"{plan['id']}.json"), plan)
            journal = self._read_json(self.journal_path, [])
            journal.insert(0, operation)
            self._write_json(self.journal_path, journal[:50])
            return operation
        except Exception:
            for file_name in created_files:
                self._remove_safe_file(Path(file_name))
            raise

    def cancel_plan(self, plan_id: str) -> Dict[str, Any]:
        plan = self._load_plan(plan_id)
        if plan.get("status") == "awaiting_approval":
            plan["status"] = "cancelled"
            plan["cancelled_at"] = int(time.time())
            self._write_json(self._safe_child(self.plans_dir, f"{plan['id']}.json"), plan)
        return plan

    def rollback_last(self) -> Dict[str, Any]:
        journal = self._read_json(self.journal_path, [])
        operation: Optional[Dict[str, Any]] = next(
            (item for item in journal if item.get("status") == "completed" and item.get("rollback_available")),
            None,
        )
        if operation is None:
            raise DeckMateError("There is no reversible DeckMate operation to undo.")
        removed: List[str] = []
        for file_name in operation.get("created_files", []):
            path = Path(file_name)
            if path.exists():
                self._remove_safe_file(path)
                removed.append(str(path))
        operation["status"] = "rolled_back"
        operation["rolled_back_at"] = int(time.time())
        operation["removed_files"] = removed
        self._write_json(self.journal_path, journal)
        return operation

    def history(self) -> List[Dict[str, Any]]:
        return self._read_json(self.journal_path, [])

    def scan_games(self) -> List[Dict[str, str]]:
        roots = [
            self.user_home / ".local/share/Steam/steamapps",
            self.user_home / ".steam/steam/steamapps",
        ]
        seen = set()
        games: List[Dict[str, str]] = []
        for root in roots:
            if not root.exists():
                continue
            for manifest in sorted(root.glob("appmanifest_*.acf")):
                try:
                    text = manifest.read_text(encoding="utf-8", errors="replace")
                    app_id = self._acf_value(text, "appid") or manifest.stem.replace("appmanifest_", "")
                    if app_id in seen:
                        continue
                    seen.add(app_id)
                    games.append(
                        {
                            "appid": app_id,
                            "name": self._acf_value(text, "name") or f"Steam app {app_id}",
                            "installdir": self._acf_value(text, "installdir") or "",
                            "library": str(root),
                        }
                    )
                except OSError:
                    continue
        return sorted(games, key=lambda game: game["name"].lower())

    @staticmethod
    def _acf_value(text: str, key: str) -> Optional[str]:
        match = re.search(rf'^\s*"{re.escape(key)}"\s+"([^"]*)"', text, re.MULTILINE | re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _classify(prompt: str) -> str:
        if any(word in prompt for word in ("emudeck", "emulation", "emulator", "rom")):
            return "emulation"
        if any(word in prompt for word in ("mod", "nexus", "smapi")):
            return "modding"
        if any(word in prompt for word in ("fsr", "frame generation", "framegen", "gamescope")):
            return "graphics"
        if any(word in prompt for word in ("proton", "compatibility", "wine")):
            return "compatibility"
        if any(word in prompt for word in ("games", "library", "installed")):
            return "library"
        return "general"

    @staticmethod
    def _title_for(topic: str) -> str:
        return {
            "emulation": "Prepare an emulation setup",
            "modding": "Prepare a safe mod installation",
            "graphics": "Prepare game graphics tuning",
            "compatibility": "Prepare a Proton compatibility change",
            "library": "Inspect the Steam library",
            "general": "Inspect and plan the request",
        }[topic]

    @staticmethod
    def _summary_for(topic: str, prompt: str) -> str:
        if topic == "library":
            return "DeckMate will read local Steam manifests and return the installed-game list."
        return (
            f'DeckMate classified “{prompt}” as {topic}. This proof of concept will inspect the library '
            "and create a reversible receipt without changing Steam, games, or system files."
        )

    @staticmethod
    def _limitations_for(topic: str) -> List[str]:
        base = ["No arbitrary shell commands", "No root filesystem changes", "No game files changed in v0.1"]
        if topic == "emulation":
            base.append("ROMs and BIOS files must be supplied legally by the user")
        if topic == "modding":
            base.append("Downloads and game-specific adapters are not enabled in the first proof of concept")
        return base

    def _load_plan(self, plan_id: str) -> Dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{12}", plan_id):
            raise DeckMateError("Invalid plan identifier.")
        path = self._safe_child(self.plans_dir, f"{plan_id}.json")
        if not path.exists():
            raise DeckMateError("Plan not found.")
        return self._read_json(path, {})

    def _safe_child(self, root: Path, name: str) -> Path:
        path = (root / name).resolve()
        if path != root and root not in path.parents:
            raise DeckMateError("Blocked path outside DeckMate state.")
        return path

    def _remove_safe_file(self, path: Path) -> None:
        resolved = path.resolve()
        if self.state_dir not in resolved.parents:
            raise DeckMateError("Rollback refused a path outside DeckMate state.")
        if resolved.is_file():
            resolved.unlink()

    @staticmethod
    def _read_json(path: Path, fallback: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
