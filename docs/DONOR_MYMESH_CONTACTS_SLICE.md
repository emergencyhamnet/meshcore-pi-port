# Donor MyMesh Contacts Slice

This slice extends the controlled donor command probe from handshake replies into the first iterator-driven contact sync path.

Scope for this slice:

1. inject one framed `CMD_GET_CONTACTS` request after the earlier command probes
2. run the donor loop enough times to emit the iterator start, one contact reply, and the end-of-contacts marker
3. verify the framed reply sequence and the saved probe contact payload

Validated fields in this slice:

1. `RESP_CODE_CONTACTS_START` and the total contact count
2. one `RESP_CODE_CONTACT` payload sourced from the saved probe contact
3. public key prefix, type, flags, out-path, name, timestamps, and saved GPS coordinates
4. `RESP_CODE_END_OF_CONTACTS` and the most recent `lastmod`

Why this slice matters:

1. it proves donor iterator-driven serial replies now work through the Pi-owned transport seam
2. it validates that the donor runtime is loading and exposing persisted contacts, not just fixed handshake state
3. it keeps validation non-radio and tightly scoped to one reversible command path