# Donor DataStore Probe Slice

This slice adds the first Pi-owned wrapper that includes donor `DataStore.h` and binds its constructor inputs without attaching any mesh runtime objects.

Scope for this slice:

1. add a Pi-owned `DataStoreHost` implementation for probe-only binding
2. add a Pi-owned `DataStore` probe that constructs donor `DataStore` with the primary and optional secondary filesystem adapters plus donor RTC adapter
3. extend the companion entrypoint to fail fast if the constructor-side probe cannot bind

Why this slice matters:

1. it proves the current host shims are sufficient for the first real donor storage object
2. it isolates remaining donor storage work to runtime behavior rather than constructor compatibility
3. it keeps `MyMesh` and radio runtime untouched

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `MyMesh.*`
3. any packet, mesh, or radio behavior changes
4. any gateway-facing runtime features