# Donor MyMesh Device Query Slice

This slice extends the controlled donor command probe from `CMD_GET_DEVICE_TIME` into `CMD_DEVICE_QUERY`.

Scope for this slice:

1. inject one framed `CMD_DEVICE_QUERY` request after the existing time probe
2. run one additional donor `MyMesh::loop()` pass
3. verify the emitted framed `RESP_CODE_DEVICE_INFO` payload shape and key fields

Validated fields in this slice:

1. response code and payload length
2. donor firmware protocol version code
3. contact-slot and group-channel counts exposed to the app
4. persisted `ble_pin`, `client_repeat`, and `path_hash_mode` values
5. donor build date, firmware version, and Pi probe board manufacturer string

Why this slice matters:

1. it proves a richer donor command reply path above the earlier time response
2. it confirms that donor command formatting is reading both board identity and persisted prefs through the Pi-owned host seams
3. it keeps validation in a fully controlled serial-command path without widening into live mesh traffic