# Hardware Parity Slice

This document defines the second commit boundary for the Pi port.

Scope for this slice:

1. express the custom HAT pin map in Pi-owned code
2. express the SPI0 bus settings in Pi-owned code
3. express reset, busy, TX enable, and RX enable control in Pi-owned code
4. keep donor companion behavior unchanged

The donor reference for this slice is `variants/generic-e22/target.h` and `variants/generic-e22/target.cpp`.

Pi HAT mapping for this slice:

1. `NSS = GPIO8`
2. `DIO1 = GPIO25`
3. `RESET = GPIO17`
4. `BUSY = GPIO24`
5. `TXEN = GPIO22`
6. `RXEN = GPIO27`
7. `SPI = SPI0`

Out of scope for this slice:

1. donor companion command changes
2. contact, advert, message, ACK, or routing changes
3. gateway-facing feature additions
4. EMP-specific runtime behavior