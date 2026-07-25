# DeckMate

DeckMate is a controller-friendly setup assistant for Steam Deck Gaming Mode, delivered as a Decky Loader plugin.

## v0.1 proof of concept

This build validates the complete Decky interaction loop:

1. Enter a request from Gaming Mode.
2. DeckMate classifies it as library, compatibility, graphics, modding, emulation, or general setup.
3. It discovers locally installed Steam games from app manifests.
4. It creates a typed action plan.
5. The user reviews and approves or cancels the plan.
6. DeckMate executes allowlisted actions and records an operation receipt.
7. The last reversible operation can be rolled back.

### Deliberate safety limits

- The plugin does **not** request Decky root access.
- Arbitrary shell commands do not exist.
- Writes are restricted to DeckMate's private settings directory.
- v0.1 does not modify Steam, game, Proton, emulator, or system files.
- Unsupported actions are rejected by the backend even if a frontend asks for them.

These limits make the first on-device test safe. Real adapters for GE-Proton, launch options, EmuDeck, and supported mods will be added one at a time with backups and rollback.

## Source layout

```text
src/index.tsx          Decky Gaming Mode UI
main.py               Decky RPC adapter
deckmate_core.py      Safe planner, game discovery, executor and rollback
tests/                Dependency-free backend tests
scripts/demo.py       Runnable command-line demonstration
scripts/package.py    Decky ZIP packager
```

## Local verification

```bash
npx --yes pnpm@9 install
npx --yes pnpm@9 run typecheck
npx --yes pnpm@9 run build
python3 -m unittest discover -s tests -v
python3 scripts/demo.py
python3 scripts/package.py
```

## Install on a Steam Deck

### Decky Developer installation

1. Install Decky Loader from [decky.xyz](https://decky.xyz/) if it is not already installed.
2. Copy `deckmate-v0.1.0.zip` to the Steam Deck.
3. In Decky settings, enable Developer Mode.
4. Open the Developer section and choose **Install Plugin from ZIP**.
5. Select the DeckMate ZIP and install it.
6. Open the Quick Access menu (`…`) and select DeckMate.

If the local ZIP installer is unavailable in the installed Decky version, extract the `DeckMate` directory to:

```text
/home/deck/homebrew/plugins/DeckMate
```

Then restart Decky/PluginLoader or reboot the Deck. Exact developer controls can vary by Decky release.

## First device test

Use these prompts first:

- `Show my installed Steam games`
- `Install GE-Proton for my selected game`
- `Set up FSR for my selected game`
- `Set up EmuDeck and emulation`

Only the library scan is real in v0.1. The other prompts create a reversible proof receipt and clearly state that no game files were changed.

## Roadmap

1. Hermes API integration with structured JSON plans
2. Selected/running Steam game detection
3. GE-Proton installation adapter
4. Per-game compatibility-tool selection
5. Gamescope/FSR launch-option adapter
6. EmuDeck bootstrap and validation adapter
7. Supported mod adapters with backup and restore
8. Voice capture and remote faster-whisper transcription

## Development principle

The LLM may choose among typed tools, but it never receives an unrestricted root shell. Each new adapter must define validation, preview, execution, verification, and rollback.
