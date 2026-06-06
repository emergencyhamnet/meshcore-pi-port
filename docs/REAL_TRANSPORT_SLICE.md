# Real Transport Slice

This slice upgrades the Pi-owned transport seam from buffer-only structure to Linux-backed transport I/O.

Scope for this slice:

1. keep the existing donor frame codec unchanged
2. add Linux serial backing for `serial://...` endpoints
3. add Linux TCP backing for `tcp://host:port` endpoints
4. keep the implementation entirely inside Pi-owned transport files

What remains unchanged:

1. donor companion command semantics
2. donor push-event semantics
3. donor runtime binding
4. gateway-facing functionality

Out of scope for this slice:

1. edits to donor `ArduinoSerialInterface.*`
2. edits to donor `BaseSerialInterface.h`
3. edits to `MyMesh.*`
4. any policy above the transport seam