# Porting Rules

This repository exists to port donor MeshCore code to Raspberry Pi.

Hard rules:

1. Do not add gateway-specific functionality here.
2. Do not change MeshCore node semantics unless a proven Pi platform blocker leaves no other option.
3. Keep the basestation boundary limited to the donor MeshCore API.
4. Prefer new Pi-owned files over edits to donor behavior files.
5. If a change would break swapability with a mainstream MeshCore companion node, reject it.

Pull request gate:

1. State the upstream release or commit used as the base.
2. Classify changed files as upstream-owned, Pi-owned, or packaging-only.
3. Explain any edit to donor behavior files.
4. Prove the change does not add new gateway-facing runtime features.