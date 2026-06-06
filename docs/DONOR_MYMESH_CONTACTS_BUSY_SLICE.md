# Donor MyMesh Contacts Busy Slice

This slice extends the contacts command family into the iterator busy-state error path.

Scope for this slice:

1. inject one framed `CMD_GET_CONTACTS` request to start the donor iterator
2. inject a second `CMD_GET_CONTACTS` request before the iterator is drained
3. verify the framed `RESP_CODE_ERR` / `ERR_CODE_BAD_STATE` reply
4. then continue with the existing normal and filtered contact-sync probes

Validated behavior in this slice:

1. the donor runtime rejects a repeated contacts request while `_iter_started` is still true
2. the error is surfaced through the same companion framing path as other command replies
3. the iterator can still be drained and reused afterward for the existing contact-sync checks

Why this slice matters:

1. it covers the first stateful error path in the donor command surface
2. it proves the contacts iterator lifecycle, not just its success cases
3. it keeps the next adjacent step within the same donor command family if we want to cover channel queries next