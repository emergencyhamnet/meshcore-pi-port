# Runtime Boot Slice

This document defines the third commit boundary for the Pi port.

Scope for this slice:

1. create a Pi-owned runtime boot state
2. make storage layout explicit in Pi-owned code
3. initialize storage directories needed for identity, state, channels, and logs
4. define the runtime endpoint as Pi-owned configuration

The donor reference for this slice is the donor startup shape in `examples/companion_radio/main.cpp` and the donor persistence role in `examples/companion_radio/DataStore.*`.

Out of scope for this slice:

1. donor companion command changes
2. edits to `MyMesh.cpp` or `MyMesh.h`
3. contact, advert, message, ACK, or routing changes
4. gateway-facing feature additions