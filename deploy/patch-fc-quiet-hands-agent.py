#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

IMPORT_ANCHOR = "import { DesktopCommanderAdapter } from './desktop-commander-adapter.js';"
IMPORT_LINE = "import { PlayableOperatorAdapter } from './playable-operator-adapter.js';"

OLD_INIT = """const adapter = new DesktopCommanderAdapter(config.desktop_commander_root);
await adapter.initialize();
const capabilities = await adapter.listTools();
"""

NEW_INIT = """const adapter = new DesktopCommanderAdapter(config.desktop_commander_root);
await adapter.initialize();

const toolAdapters = new Map();
const capabilities = [];

async function addAdapter(owner) {
  const tools = await owner.listTools();
  for (const tool of tools) {
    if (!tool?.name) continue;
    if (toolAdapters.has(tool.name)) {
      throw new Error(`duplicate Quiet Hands tool name from local adapters: ${tool.name}`);
    }
    toolAdapters.set(tool.name, owner);
    capabilities.push(tool);
  }
}

await addAdapter(adapter);

const playableOperatorSocket = process.env.QUIET_HANDS_PLAYABLE_OPERATOR_SOCKET ?? '';
let playableOperatorAdapter = null;
if (playableOperatorSocket) {
  playableOperatorAdapter = new PlayableOperatorAdapter(playableOperatorSocket);
  await playableOperatorAdapter.initialize();
  await addAdapter(playableOperatorAdapter);
}
"""

OLD_CALL = """    const result = await adapter.callTool(call.tool_name, call.arguments ?? {}, {
      quiet_hands_call_id: callId,
      quiet_hands_node_id: config.node_id
    });"""

NEW_CALL = """    const selectedAdapter = toolAdapters.get(call.tool_name);
    if (!selectedAdapter) {
      throw new Error(`tool not owned by any local adapter: ${call.tool_name}`);
    }
    const result = await selectedAdapter.callTool(call.tool_name, call.arguments ?? {}, {
      quiet_hands_call_id: callId,
      quiet_hands_node_id: config.node_id
    });"""

OLD_CLOSE = """  await adapter.close();
  process.exit(0);"""

NEW_CLOSE = """  if (playableOperatorAdapter) await playableOperatorAdapter.close();
  await adapter.close();
  process.exit(0);"""


def patch(path: Path) -> None:
    text = path.read_text()

    if IMPORT_LINE not in text:
        if IMPORT_ANCHOR not in text:
            raise SystemExit(f"REFUSED: import anchor missing in {path}")
        text = text.replace(
            IMPORT_ANCHOR,
            IMPORT_ANCHOR + "\n" + IMPORT_LINE,
            1,
        )

    if "const toolAdapters = new Map();" not in text:
        if OLD_INIT not in text:
            raise SystemExit(f"REFUSED: init anchor missing in {path}")
        text = text.replace(OLD_INIT, NEW_INIT, 1)

    if "const selectedAdapter = toolAdapters.get(call.tool_name);" not in text:
        if OLD_CALL not in text:
            raise SystemExit(f"REFUSED: call anchor missing in {path}")
        text = text.replace(OLD_CALL, NEW_CALL, 1)

    if "playableOperatorAdapter.close()" not in text:
        if OLD_CLOSE not in text:
            raise SystemExit(f"REFUSED: close anchor missing in {path}")
        text = text.replace(OLD_CLOSE, NEW_CLOSE, 1)

    path.write_text(text)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: patch-fc-quiet-hands-agent.py AGENT_JS [AGENT_JS ...]", file=sys.stderr)
        return 2
    for name in sys.argv[1:]:
        patch(Path(name))
        print(f"patched={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
