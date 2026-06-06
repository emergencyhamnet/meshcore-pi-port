# Donor MyMesh Constructor Slice

This slice adds the first donor runtime probe above storage by constructing donor `MyMesh` and binding its serial interface without entering the full runtime loop.

Scope for this slice:

1. add minimal host-side compatibility stubs needed to include donor `MyMesh.h`
2. add a Pi-owned `MyMesh` probe that constructs donor `MyMesh` with the current donor RTC, serial, and `DataStore` probes
3. verify `startInterface()` enables the donor serial attachment and exposes node prefs

Why this slice matters:

1. it proves the first real donor runtime object above storage can bind on the Pi-owned side
2. it keeps the step constructor-side and interface-side, without entering donor loop or radio behavior
3. it identifies the next remaining gap as runtime execution, not basic object attachment

Out of scope for this slice:

1. edits to donor `MyMesh.*`
2. any donor radio loop execution
3. any packet or mesh behavior changes
4. any gateway-facing runtime features