# Donor Host Contracts Slice

This slice defines the first explicit donor-host binding contracts on the Pi-owned side.

Scope for this slice:

1. define Pi-owned board, storage, and serial host interfaces
2. define Pi-owned concrete host wrappers over the current bridge and transport seams
3. bind those contracts above the donor runtime bridge without attaching any real donor runtime objects yet

Why this slice matters:

1. it creates a narrow, named attachment surface for future donor hosting
2. it prevents later donor integration from reaching directly into arbitrary Pi internals
3. it keeps the port donor-aligned by separating platform hosting contracts from donor behavior

Out of scope for this slice:

1. edits to donor `MyMesh.*`
2. edits to donor `DataStore.*`
3. edits to donor serial protocol semantics
4. any gateway-facing runtime features