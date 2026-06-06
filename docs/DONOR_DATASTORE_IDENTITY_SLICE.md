# Donor DataStore Identity Slice

This slice advances the donor storage probe from blob-store setup to the first identity persistence cycle.

Scope for this slice:

1. force donor `_main.id` absent before the probe so the missing-file path is deterministic
2. verify donor `loadMainIdentity()` reports absence before save
3. verify donor `saveMainIdentity()` creates `_main.id` and donor `loadMainIdentity()` succeeds afterward

Why this slice matters:

1. it proves the host filesystem and donor `IdentityStore` path mapping are aligned
2. it exercises both donor identity load and save paths without attaching any mesh runtime objects
3. it keeps the next step focused on prefs or channel/contact behavior rather than identity persistence

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `IdentityStore.*`
3. any `MyMesh` attachment
4. any gateway-facing runtime features