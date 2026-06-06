# Donor MyMesh Channel Slice

This slice extends the persisted-data command probes into `CMD_GET_CHANNEL`.

Scope for this slice:

1. inject one framed `CMD_GET_CHANNEL` request for channel index `0`
2. run one donor `MyMesh::loop()` pass
3. verify the framed `RESP_CODE_CHANNEL_INFO` reply against the saved probe channel

Validated fields in this slice:

1. response code, payload length, and requested channel index
2. persisted channel name
3. first 128 bits of the saved channel secret, which is what the donor command surface exports

Why this slice matters:

1. it proves the donor runtime is exposing persisted channel data through the companion command interface
2. it stays on the same non-radio persisted-state surface as the recent contacts work
3. it keeps the next adjacent step open for a channel not-found error path if we want that before Pi-native runtime bring-up