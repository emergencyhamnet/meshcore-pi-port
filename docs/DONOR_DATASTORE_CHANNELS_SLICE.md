# Donor DataStore Channels Slice

This slice advances the donor storage probe from contacts persistence to the first channels round-trip.

Scope for this slice:

1. save one deterministic donor `ChannelDetails` record through `DataStore::saveChannels()`
2. verify `/channels2` is created on the active channels filesystem
3. load the record back through donor `DataStoreHost` callbacks and compare it against the saved channel

Why this slice matters:

1. it proves the remaining donor `DataStoreHost` callback path works through the Pi-owned storage mapping
2. it exercises donor channel record persistence without attaching mesh runtime objects
3. it closes the constructor and storage-behavior validation loop before stepping toward runtime-owned donor objects

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. any `MyMesh` attachment
3. any packet, mesh, or radio behavior changes
4. any gateway-facing runtime features