# Pi Browser UI Move Plan

This plan moves the new browser UI into its final home on the Pi while retiring the old local management UI and keeping the basestation gateway path intact.

## Keep And Remove

Keep these Pi services:

1. `meshcore-pi-live-runtime.service` for the runtime and native companion endpoint on `127.0.0.1:5040`
2. `meshcore-pi-gateway-link.service` for the EHN/basestation gateway-facing pipe

Retire this old local management UI surface:

1. `meshcore-pi-node-ui.service` if it exists
2. the old Pi-local management UI port after the service is stopped and removed

Install this as the final browser UI surface:

1. `meshcore-pi-browser-ui.service`
2. direct bind on the Pi without reverse proxy or extra network security, because this deployment is intentionally limited to the closed network

## Final Service Layout

Recommended ports and roles:

1. `127.0.0.1:5040` native companion endpoint owned by the runtime
2. `0.0.0.0:7463` basestation gateway link for EHN work, preferably hosted by the browser UI through the same broker
3. `0.0.0.0:8099` final Pi-hosted browser UI

This keeps the browser UI and basestation gateway as separate surfaces with separate purposes.
It avoids opening separate native companion sessions when both surfaces are active.

## Current Live Deployment Note

The live Pi used during current EHN work is not running from `/opt/meshcore-pi-port`.

Current known-good live deployment details are:

1. live repo path is `/home/n2dh/meshcore-pi-port`
2. `meshcore-pi-browser-ui.service` has `WorkingDirectory=/home/n2dh/meshcore-pi-port`
3. `meshcore-pi-browser-ui.service` launches `/home/n2dh/meshcore-pi-port/scripts/run-pi-browser-ui.sh`
4. that browser-ui service currently has `MESHCORE_PI_BROWSER_UI_ENABLE_GATEWAY_LINK=1`
5. that browser-ui service is configured to expose the embedded basestation gateway listener on `0.0.0.0:7463`

Practical consequence:

1. if Pi-side gateway-link behavior looks unchanged after a Windows fix, first confirm that the updated file was copied into `/home/n2dh/meshcore-pi-port`
2. do not assume `/opt/meshcore-pi-port` is the active deployment path unless `systemctl cat` proves it
3. when in doubt, trust `systemctl cat meshcore-pi-browser-ui.service` and `systemctl cat meshcore-pi-gateway-link.service` over memory

## Deployment Steps

1. Copy the current repo contents to the live Pi path.
2. Retire the old local management UI with `sudo bash scripts/retire-pi-management-ui.sh`.
3. Install or refresh the runtime service with `sudo env MESHCORE_PI_INTERFACE_MODE=app bash scripts/install-pi-live-runtime-service.sh`.
4. Install the new browser UI service with `sudo bash scripts/install-pi-browser-ui-service.sh`.
5. Leave basestation transmit disabled by default on the embedded gateway listener unless you deliberately enable it.
6. Stop the separate gateway-link service if it is still installed and you want the shared-broker layout to own `7463`.
7. Start the runtime first, then the browser UI, and confirm the embedded gateway listener is healthy.

For the current live Pi, the most common recovery path is narrower:

1. back up the live file or tree under `/home/n2dh/meshcore-pi-port`
2. copy the updated file into `/home/n2dh/meshcore-pi-port/ui-native/src/meshcore_ui_native/`
3. restart `meshcore-pi-browser-ui.service`
4. only restart `meshcore-pi-gateway-link.service` if `systemctl` or `ss` shows it is the real owner of `7463`

Backup examples for the current live layout:

```bash
cd /home/n2dh/meshcore-pi-port
sudo cp ui-native/src/meshcore_ui_native/gateway_link_server.py \
ui-native/src/meshcore_ui_native/gateway_link_server.py.bak-$(date +%Y%m%d-%H%M%S)
```

```bash
cd /home/n2dh
sudo cp -a meshcore-pi-port meshcore-pi-port.bak-$(date +%Y%m%d-%H%M%S)
```

## Start Stop Monitor

Start:

```bash
sudo systemctl start meshcore-pi-live-runtime.service
sudo systemctl start meshcore-pi-browser-ui.service
```

Stop:

```bash
sudo systemctl stop meshcore-pi-browser-ui.service
sudo systemctl stop meshcore-pi-gateway-link.service
sudo systemctl stop meshcore-pi-live-runtime.service
```

Monitor:

```bash
sudo systemctl status meshcore-pi-browser-ui.service --no-pager
sudo systemctl status meshcore-pi-live-runtime.service --no-pager
sudo systemctl status meshcore-pi-gateway-link.service --no-pager
sudo journalctl -u meshcore-pi-browser-ui.service -n 50 --no-pager
sudo journalctl -u meshcore-pi-live-runtime.service -n 50 --no-pager
sudo journalctl -u meshcore-pi-gateway-link.service -n 50 --no-pager
```

Follow live logs when needed:

```bash
sudo journalctl -u meshcore-pi-browser-ui.service -f
```

Useful ownership checks before restart:

```bash
sudo systemctl cat meshcore-pi-browser-ui.service
sudo systemctl cat meshcore-pi-gateway-link.service
sudo ss -ltnp | grep 7463
```

## Logging And Debug Integration

The browser UI already carries operator-facing debug information through the native session broker and live tool-log panel.

Pi-side integration should use:

1. systemd restart and failure reporting for process supervision
2. journalctl for browser-service lifecycle and stderr/stdout capture
3. the existing browser Tools debug-log area for native `PACKET_LOG_DATA` visibility
4. the runtime status file and runtime service journal for lower-level companion and runtime issues

No extra reverse proxy logging layer is required for this closed-network deployment.

## Validation After Move

1. Open `http://<pi-host>:8099/`.
2. Confirm Settings, Contacts, Channels, and Tools render with live node data.
3. Confirm direct-message TX/RX still works from the Pi-hosted browser UI.
4. Confirm the basestation-facing EHN path still works through `7463`.
5. Confirm the old Pi management UI is no longer running.