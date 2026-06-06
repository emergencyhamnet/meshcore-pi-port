# Donor Storage Compatibility Slice

This slice adds the first donor-facing storage compatibility object on top of the Pi-owned host contracts.

Scope for this slice:

1. extend the Pi-owned storage host contract with path ownership and clock methods
2. add a Pi-owned adapter that implements donor `mesh::RTCClock`
3. bind that donor-facing RTC adapter above the existing storage host wrapper

Why this slice matters:

1. it proves the Pi port can satisfy a second real upstream base type without editing donor behavior
2. it captures the storage path ownership that a later `FILESYSTEM` wrapper will need
3. it keeps the `DataStore` decision narrow by deferring only the unresolved filesystem-type mapping

Out of scope for this slice:

1. edits to donor `DataStore.*`
2. edits to donor `IdentityStore.*`
3. introduction of a fake donor filesystem implementation
4. any gateway-facing runtime features