# Donor DataStore Begin Slice

This slice advances the donor storage probe from constructor binding to the first safe behavior call.

Scope for this slice:

1. call donor `DataStore::begin()` through the Pi-owned probe wrapper
2. verify that the expected blob-store directory is created through the host filesystem shim
3. fail the probe if the constructor succeeds but the first storage-side behavior does not

Why this slice matters:

1. it proves the host filesystem mapping is good enough for the first real donor storage behavior
2. it exercises donor-owned code paths without attaching any mesh runtime objects
3. it keeps the next decision focused on identity or prefs behavior instead of constructor compatibility

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `IdentityStore.*`
3. any `MyMesh` attachment
4. any gateway-facing runtime features