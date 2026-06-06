# Donor MyMesh Channel Missing Slice

This slice extends the channel command probe into the `CMD_GET_CHANNEL` not-found error path.

Scope for this slice:

1. inject one framed `CMD_GET_CHANNEL` request for a missing channel index
2. run one donor `MyMesh::loop()` pass
3. verify the framed `RESP_CODE_ERR` / `ERR_CODE_NOT_FOUND` reply

Validated behavior in this slice:

1. the donor runtime returns the expected companion error frame when a channel index is absent
2. the persisted channel success path and the missing-index error path both coexist in the same probe run
3. channel lookup remains on the same non-radio persisted-state surface as the recent contacts and channel readback work

Why this slice matters:

1. it completes the first paired success and error coverage for donor channel lookup
2. it gives us one more stateful command-path check before switching to a mutating command or Pi-native execution
3. it keeps the remaining host-side work narrow and directly tied to donor companion behavior