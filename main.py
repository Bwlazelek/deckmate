import decky

from deckmate_core import DeckMateCore, DeckMateError


class Plugin:
    async def _main(self):
        self.core = DeckMateCore(decky.DECKY_SETTINGS_DIR, decky.DECKY_USER_HOME)
        decky.logger.info("DeckMate v0.1 started in safe non-root mode")

    async def _unload(self):
        decky.logger.info("DeckMate unloaded")

    async def get_status(self):
        return self.core.status()

    async def submit_prompt(self, prompt: str):
        try:
            return {"ok": True, "plan": self.core.create_plan(prompt)}
        except DeckMateError as error:
            return {"ok": False, "error": str(error)}

    async def execute_plan(self, plan_id: str):
        try:
            return {"ok": True, "operation": self.core.execute_plan(plan_id)}
        except DeckMateError as error:
            return {"ok": False, "error": str(error)}

    async def cancel_plan(self, plan_id: str):
        try:
            return {"ok": True, "plan": self.core.cancel_plan(plan_id)}
        except DeckMateError as error:
            return {"ok": False, "error": str(error)}

    async def rollback_last(self):
        try:
            return {"ok": True, "operation": self.core.rollback_last()}
        except DeckMateError as error:
            return {"ok": False, "error": str(error)}

    async def get_history(self):
        return self.core.history()

    async def get_games(self):
        return self.core.scan_games()
