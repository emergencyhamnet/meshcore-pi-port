# Donor MyMesh Command Slice

This slice advances the donor runtime probe from startup into the first controlled command-handling path.

Scope for this slice:

1. inject one framed `CMD_GET_DEVICE_TIME` request through the Pi transport seam
2. run one donor `MyMesh::loop()` pass to consume that request
3. verify that donor command handling emits the expected framed `RESP_CODE_CURR_TIME` reply

Why this slice matters:

1. it proves donor serial command handling now works through the Pi-owned transport and serial adapters
2. it exercises donor runtime behavior beyond `begin(false)` without stepping into live radio flow
3. it keeps the next decision focused on deeper command paths or controlled outbound behaviors rather than basic interface viability

Out of scope for this slice:

1. edits to donor `MyMesh.*`
2. any live radio receive or transmit behavior
3. any gateway-facing runtime features
4. broad donor loop execution beyond this single controlled command pass