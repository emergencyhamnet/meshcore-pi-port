# Donor Serial Interface Slice

This slice adds the first real donor-facing object binding on top of the Pi-owned host contracts.

Scope for this slice:

1. extend the Pi-owned serial host contract to cover donor `BaseSerialInterface` enable-state methods
2. add a Pi-owned adapter that implements donor `BaseSerialInterface`
3. bind that donor-facing adapter above the existing serial host wrapper

Why this slice matters:

1. it proves the Pi port can satisfy a real upstream interface without editing donor behavior
2. it keeps donor protocol framing delegated to the already validated transport seam
3. it establishes the smallest practical donor attachment point before storage or mesh runtime binding

Out of scope for this slice:

1. edits to donor `ArduinoSerialInterface.*`
2. edits to donor `MyMesh.*`
3. edits to donor `DataStore.*`
4. any gateway-facing runtime features