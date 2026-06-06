# Donor DataStore Contacts Slice

This slice advances the donor storage probe from prefs persistence to the first contacts round-trip.

Scope for this slice:

1. save one deterministic donor `ContactInfo` record through `DataStore::saveContacts()`
2. verify `/contacts3` is created on the active contacts filesystem
3. load the record back through donor `DataStoreHost` callbacks and compare it against the saved contact

Why this slice matters:

1. it proves the host storage mapping supports donor contact record persistence and callback-driven load behavior
2. it exercises the larger donor binary contact layout without attaching any mesh runtime objects
3. it keeps the next step focused on channels or higher runtime objects rather than storage callback compatibility

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `ContactInfo` behavior
3. any `MyMesh` attachment
4. any gateway-facing runtime features