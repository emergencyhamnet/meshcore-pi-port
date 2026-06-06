# Real Storage Slice

This slice upgrades one Pi-owned seam from placeholder structure to real filesystem-backed behavior.

Scope for this slice:

1. add real text-file read and write helpers in Pi-owned storage code
2. persist bridge runtime status into the Pi-owned state directory
3. keep donor runtime binding and donor behavior unchanged

Why this slice is safe:

1. it stays entirely inside Pi-owned storage and bridge files
2. it does not alter donor persistence semantics
3. it gives the port a real on-disk state artifact without crossing the donor boundary

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `MyMesh.*`
3. command or push-protocol changes
4. gateway-facing runtime features