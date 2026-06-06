# Donor DataStore Prefs Slice

This slice advances the donor storage probe from identity persistence to the first prefs round-trip.

Scope for this slice:

1. remove any existing donor prefs files so the probe is deterministic
2. save a deterministic donor `NodePrefs` payload through `DataStore::savePrefs()`
3. verify `/new_prefs` exists and donor `loadPrefs()` reads the same values back

Why this slice matters:

1. it proves the host filesystem mapping is good enough for the donor prefs binary layout
2. it exercises donor save and load behavior on a wider persisted structure than identity alone
3. it keeps the next decision focused on contacts or channels rather than prefs persistence

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `IdentityStore.*`
3. any `MyMesh` attachment
4. any gateway-facing runtime features