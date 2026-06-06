# Transport Seam Slice

This document defines the next Pi-owned slice after runtime boot.

Scope for this slice:

1. parse a Pi-owned runtime endpoint string
2. model transport readiness separately from donor mesh behavior
3. mirror donor framed transport semantics for host-side testing
4. keep the transport seam separate from gateway policy and separate from donor companion logic

The donor reference for this slice is `src/helpers/BaseSerialInterface.h` and `src/helpers/ArduinoSerialInterface.*`.

The framing preserved in this slice is:

1. outgoing frame header `>` plus 16-bit little-endian payload length
2. incoming frame header `<` plus 16-bit little-endian payload length
3. max frame payload `176`

Out of scope for this slice:

1. companion protocol changes
2. edits to `MyMesh.cpp` or `MyMesh.h`
3. gateway-facing feature additions
4. network or serial device I/O beyond the seam contract itself