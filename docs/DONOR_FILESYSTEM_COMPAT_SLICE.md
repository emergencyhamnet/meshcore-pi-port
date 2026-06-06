# Donor Filesystem Compatibility Slice

This slice adds the first host-side compatibility mapping for donor `FILESYSTEM` and `File` usage without binding `DataStore` yet.

Scope for this slice:

1. add host-side `Stream`, `File`, and `fs::FS` compatibility shims for donor storage code
2. bind Pi-owned primary and optional secondary filesystem adapters above the storage host contract
3. make the root-path mapping for donor storage explicit while leaving `DataStore` unbound

Why this slice matters:

1. it resolves the remaining constructor-side `FILESYSTEM` question to a concrete host mapping
2. it keeps the compatibility logic outside donor files
3. it isolates the next decision to actual `DataStore` attachment instead of filesystem shape discovery

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `IdentityStore.*`
3. attachment of donor `MyMesh.*`
4. any gateway-facing runtime features