# v0.2.0-alpha5

Standalone Pi E22 RF control and settings-save correction, 2026-11-01.
Supersedes alpha4 for the Raspberry Pi HAT. The alpha4 tag is unchanged.

## Corrections

- Physical GPIO22/TXEN and GPIO27/RXEN now use `lgpio` rather than the old in-memory
  simulator. GPIO initialization precedes board setup; reset/BUSY/RF-switch pins share
  ownership with the radio HAL. Receive is disabled before enabling transmit.
- Pi builds explicitly disable SX1262 DIO2 RF switching after RadioLib initialization.
  Omitting the define was insufficient because RadioLib enables DIO2 by default.
- Default and maximum SX1262 drive are +9 dBm, with a -9 dBm minimum. Saved higher values
  are clamped at startup and requests above +9 are rejected. This is a precaution based on
  the upstream E22-900M33S FAQ; independent manufacturer-limit verification is still pending.
- Save all settings no longer resends a stale device timestamp backwards, which previously
  failed before the TX-power command. MeshCore's forward-only clock rule is unchanged.
- The UI validates the power range before saving and describes the gateway listener's
  remote-TX policy without implying that a basestation is connected or local TX is disabled.
- Source packaging uses the committed Git tree, including root compatibility headers.
- Optional power tracing is off by default. It logs RadioLib status and PA/power SPI
  commands only when explicitly enabled; it does not change radio parameters.

## RF Evidence

Operator measurements using adverts on the standalone Issue 1.0 E22-900M33S HAT:

| Requested chip drive | Reported RF output |
|---:|---:|
| -9 dBm | 21.40 dBm |
| 0 dBm | 28.23 dBm |
| +3 dBm | 28.81 dBm |
| +6 dBm | 31.20 dBm |
| +9 dBm | 31.82 dBm |

The operator reports recalibration with uncertainty below 1 dB. Acquisition uses advert
bursts and spectrum-analyzer peak hold; this is not independent certification of total
conducted power. The measured adjustment is 10.42 dB. A +12 request also indicated
31.82 dBm but exceeds the accepted ceiling and is not a valid additional control point.
Earlier constant-output results did not test power adjustment because settings saves failed.
The UI value is requested chip output, not antenna-port power or hardware readback.

## Upgrade

No manual GPIO or build-flag edits are required. Source users must rebuild; rebooting alone
does not replace the old executable. On a clean installed checkout:

```bash
cd /opt/meshcore-pi-port
sudo tar -czf /root/meshcore-state-before-alpha5.tar.gz -C /var/lib meshcore-pi-port
git fetch origin --tags
git checkout v0.2.0-alpha5
MESHCORE_PI_LIVE_RUNTIME_BIN="$PWD/bin/pi-live-runtime.new" bash scripts/build-pi-live-runtime.sh
sudo systemctl stop meshcore-pi-browser-ui.service meshcore-pi-live-runtime.service
cp -a bin/pi-live-runtime bin/pi-live-runtime.before-alpha5
mv bin/pi-live-runtime.new bin/pi-live-runtime
sudo systemctl start meshcore-pi-live-runtime.service meshcore-pi-browser-ui.service
```

If checkout refuses local changes, preserve them and use a separate clean clone rather than
forcing checkout. Preserve identity, contacts, channels and preferences under
`/var/lib/meshcore-pi-port`; do not reset state as part of this upgrade.
New installations should follow [the install guide](pi_install_build_release.md).

## Scope And Limitations

The fix belongs to this Pi radio runtime and applies to both standalone and gateway use.
Updating another deployed basestation's Pi runtime is a separate operation; the basestation
application itself does not control HAT GPIO. Remote gateway TX permission remains independent
and is not enabled by this release. Existing alpha4 feature limitations remain applicable.
No prebuilt binary is certified for all Pi architectures; build from the release source.