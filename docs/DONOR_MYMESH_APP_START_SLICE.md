# Donor MyMesh App Start Slice

This slice extends the controlled donor command probe from `CMD_DEVICE_QUERY` into `CMD_APP_START`.

Scope for this slice:

1. inject one minimal framed `CMD_APP_START` request after the earlier command probes
2. run one additional donor `MyMesh::loop()` pass
3. verify the emitted framed `RESP_CODE_SELF_INFO` payload against persisted probe state

Validated fields in this slice:

1. response code and payload length
2. advert type, transmit power, and max LoRa power fields
3. stored main identity public key bytes
4. persisted latitude and longitude loaded during `begin(false)`
5. persisted multi-ack, advert location, telemetry mode, and manual-add flags
6. persisted radio settings and node name

Why this slice matters:

1. it proves donor startup reply formatting now reads identity, location, and node prefs through the Pi-owned seams
2. it covers the next app-facing handshake response without widening into live mesh traffic
3. it keeps donor validation in the same controlled serial command path used by the earlier probes