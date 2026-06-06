# Donor MyMesh Contacts Since Slice

This slice extends the contact iterator probe into the optional `since` filter path.

Scope for this slice:

1. inject one framed `CMD_GET_CONTACTS` request with a `since` value newer than the saved probe contact
2. run the donor loop enough times to advance the iterator through the filtered-out contact and emit EOF
3. verify that the donor reply sequence contains only `RESP_CODE_CONTACTS_START` and `RESP_CODE_END_OF_CONTACTS`

Validated behavior in this slice:

1. the total contact count in `RESP_CODE_CONTACTS_START` remains unfiltered
2. the saved probe contact is skipped when its `lastmod` is not newer than the supplied `since`
3. `RESP_CODE_END_OF_CONTACTS` reports `0` as the most recent emitted `lastmod` when no contact passes the filter

Why this slice matters:

1. it proves the donor iterator filter semantics, not just the happy-path contact export
2. it exercises stateful serial command behavior without widening into mesh traffic
3. it keeps the next adjacent step close to the same command family if we want to cover busy-state or repeated iterator requests