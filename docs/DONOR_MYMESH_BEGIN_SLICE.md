# Donor MyMesh Begin Slice

This slice advances the first donor runtime probe from constructor-only binding to the first controlled `MyMesh::begin(false)` behavior call.

Scope for this slice:

1. provide minimal host-side implementations for the remaining Arduino timing and random hooks used by the probe
2. call donor `MyMesh::begin(false)` through the Pi-owned runtime probe
3. verify that donor prefs persisted by the earlier `DataStore` probe are loaded into `MyMesh`

Why this slice matters:

1. it proves the first donor runtime object can execute its startup path above storage
2. it confirms `MyMesh` is consuming donor-persisted prefs through the Pi-owned storage mapping
3. it keeps the step narrowly scoped to startup behavior rather than the full loop or live radio flow

Out of scope for this slice:

1. edits to donor `MyMesh.*`
2. entering the donor `loop()` path
3. any live radio behavior
4. any gateway-facing runtime features