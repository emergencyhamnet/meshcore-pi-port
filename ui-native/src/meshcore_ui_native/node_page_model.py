from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True, slots=True)
class IdentitySection:
    name: str
    public_key: str
    model: str
    firmware_version: str
    firmware_build: str
    device_time: int
    advert_lat: float | None
    advert_lon: float | None


@dataclass(frozen=True, slots=True)
class RadioSection:
    tx_power_dbm: int
    max_tx_power_dbm: int
    freq_mhz: float
    bw_khz: float
    sf: int
    cr: int
    advert_loc_policy: int
    telemetry_mode_base: int
    telemetry_mode_loc: int
    telemetry_mode_env: int


@dataclass(frozen=True, slots=True)
class CapabilitySection:
    ble_pin: int | None
    client_repeat: int | None
    path_hash_mode: int | None
    max_contacts: int | None
    max_channels: int | None
    manual_add_contacts: bool


@dataclass(frozen=True, slots=True)
class BatterySection:
    battery_mv: int
    used_kb: int | None
    total_kb: int | None


@dataclass(frozen=True, slots=True)
class NodePageModel:
    identity: IdentitySection
    radio: RadioSection
    capabilities: CapabilitySection
    battery: BatterySection
    contacts: list[dict[str, Any]]
    channels: list[dict[str, Any]]
    custom_vars: dict[str, str]
    contacts_with_location_count: int
    provisioned_channel_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contacts"] = self.contacts
        payload["channels"] = self.channels
        payload["custom_vars"] = self.custom_vars
        return payload


def _optional_coordinate(lat: float, lon: float, value: float) -> float | None:
    if lat == 0.0 and lon == 0.0:
        return None
    return float(value)


def _is_provisioned_channel(channel: dict[str, Any]) -> bool:
    secret_hex = str(channel.get("secret_hex") or "")
    return bool(secret_hex) and any(char != "0" for char in secret_hex)


def _has_contact_location(contact: dict[str, Any]) -> bool:
    lat = float(contact.get("gps_lat") or 0.0)
    lon = float(contact.get("gps_lon") or 0.0)
    return lat != 0.0 or lon != 0.0


def build_node_page_model(snapshot: dict[str, Any]) -> NodePageModel:
    self_info = snapshot["self_info"]
    device_info = snapshot["device_info"]
    battery = snapshot["battery"]
    contacts = [contact for contact in snapshot.get("contacts", []) if isinstance(contact, dict)]
    channels = [channel for channel in snapshot.get("channels", []) if isinstance(channel, dict)]
    custom_vars = snapshot.get("custom_vars", {}) if isinstance(snapshot.get("custom_vars"), dict) else {}
    advert_lat = float(self_info.get("adv_lat") or 0.0)
    advert_lon = float(self_info.get("adv_lon") or 0.0)
    return NodePageModel(
        identity=IdentitySection(
            name=str(self_info.get("name") or ""),
            public_key=str(self_info.get("public_key") or ""),
            model=str(device_info.get("model") or ""),
            firmware_version=str(device_info.get("version") or ""),
            firmware_build=str(device_info.get("firmware_build") or ""),
            device_time=int(snapshot.get("device_time") or 0),
            advert_lat=_optional_coordinate(advert_lat, advert_lon, advert_lat),
            advert_lon=_optional_coordinate(advert_lat, advert_lon, advert_lon),
        ),
        radio=RadioSection(
            tx_power_dbm=int(self_info.get("tx_power") or 0),
            max_tx_power_dbm=int(self_info.get("max_tx_power") or 0),
            freq_mhz=float(self_info.get("radio_freq_mhz") or 0.0),
            bw_khz=float(self_info.get("radio_bw_khz") or 0.0),
            sf=int(self_info.get("radio_sf") or 0),
            cr=int(self_info.get("radio_cr") or 0),
            advert_loc_policy=int(self_info.get("advert_loc_policy") or 0),
            telemetry_mode_base=int(self_info.get("telemetry_mode_base") or 0),
            telemetry_mode_loc=int(self_info.get("telemetry_mode_loc") or 0),
            telemetry_mode_env=int(self_info.get("telemetry_mode_env") or 0),
        ),
        capabilities=CapabilitySection(
            ble_pin=device_info.get("ble_pin"),
            client_repeat=device_info.get("client_repeat"),
            path_hash_mode=device_info.get("path_hash_mode"),
            max_contacts=device_info.get("max_contacts"),
            max_channels=device_info.get("max_channels"),
            manual_add_contacts=bool(self_info.get("manual_add_contacts")),
        ),
        battery=BatterySection(
            battery_mv=int(battery.get("battery_mv") or 0),
            used_kb=battery.get("used_kb"),
            total_kb=battery.get("total_kb"),
        ),
        contacts=contacts,
        channels=channels,
        custom_vars={str(key): str(value) for key, value in custom_vars.items()},
        contacts_with_location_count=sum(1 for contact in contacts if _has_contact_location(contact)),
        provisioned_channel_count=sum(1 for channel in channels if _is_provisioned_channel(channel)),
    )