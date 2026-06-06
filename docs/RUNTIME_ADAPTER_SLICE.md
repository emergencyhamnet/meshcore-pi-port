# Runtime Adapter Slice

This document defines the next Pi-owned slice after the transport seam.

Scope for this slice:

1. add a Pi-owned runtime adapter that starts the boot state and transport seam together
2. mirror the donor role of `startInterface` without changing donor protocol semantics
3. keep transport lifecycle separate from gateway policy and separate from donor mesh behavior

The donor reference for this slice is the use of `BaseSerialInterface` and `startInterface(...)` in `examples/companion_radio/main.cpp` and `examples/companion_radio/MyMesh.h`.

Out of scope for this slice:

1. edits to `MyMesh.cpp` or `MyMesh.h`
2. changes to donor command or push semantics
3. gateway-facing feature additions
4. real donor runtime integration beyond the adapter seam itself