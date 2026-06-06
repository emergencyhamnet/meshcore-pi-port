# Donor Runtime Bridge Slice

This document defines the next Pi-owned slice after the runtime adapter.

Scope for this slice:

1. add a Pi-owned bridge state above the runtime adapter
2. create one future attachment point for donor runtime objects
3. keep donor runtime binding explicitly absent until a later slice
4. keep Pi lifecycle orchestration separate from donor MeshCore behavior

The intent is to give the future donor runtime one Pi-owned hosting seam without moving any donor logic into Pi files.

Out of scope for this slice:

1. edits to donor companion logic
2. edits to `MyMesh.cpp` or `MyMesh.h`
3. command or push-protocol changes
4. gateway-facing runtime features