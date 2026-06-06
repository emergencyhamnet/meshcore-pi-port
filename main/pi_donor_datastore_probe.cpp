#include "pi_donor_datastore_probe.h"

#include <cstring>

namespace pi_port {

namespace {

NodePrefs build_probe_prefs() {
    NodePrefs prefs{};
    prefs.airtime_factor = 1.75f;
    std::strcpy(prefs.node_name, "pi-port-probe");
    prefs.freq = 915.5f;
    prefs.sf = 9;
    prefs.cr = 5;
    prefs.multi_acks = 1;
    prefs.manual_add_contacts = 1;
    prefs.bw = 250.0f;
    prefs.tx_power_dbm = 17;
    prefs.telemetry_mode_base = TELEM_MODE_ALLOW_ALL;
    prefs.telemetry_mode_loc = TELEM_MODE_ALLOW_FLAGS;
    prefs.telemetry_mode_env = TELEM_MODE_DENY;
    prefs.rx_delay_base = 2.5f;
    prefs.ble_pin = 123456;
    prefs.advert_loc_policy = ADVERT_LOC_SHARE;
    prefs.buzzer_quiet = 1;
    prefs.gps_enabled = 1;
    prefs.gps_interval = 300;
    prefs.autoadd_config = 3;
    prefs.rx_boosted_gain = 1;
    prefs.client_repeat = 2;
    prefs.path_hash_mode = 1;
    prefs.autoadd_max_hops = 4;
    std::strcpy(prefs.default_scope_name, "ehn-primary");
    for (std::size_t index = 0; index < sizeof(prefs.default_scope_key); ++index) {
        prefs.default_scope_key[index] = static_cast<std::uint8_t>(index + 1U);
    }
    return prefs;
}

bool prefs_equal(const NodePrefs& left, const NodePrefs& right) {
    return left.airtime_factor == right.airtime_factor
        && std::memcmp(left.node_name, right.node_name, sizeof(left.node_name)) == 0
        && left.freq == right.freq
        && left.sf == right.sf
        && left.cr == right.cr
        && left.multi_acks == right.multi_acks
        && left.manual_add_contacts == right.manual_add_contacts
        && left.bw == right.bw
        && left.tx_power_dbm == right.tx_power_dbm
        && left.telemetry_mode_base == right.telemetry_mode_base
        && left.telemetry_mode_loc == right.telemetry_mode_loc
        && left.telemetry_mode_env == right.telemetry_mode_env
        && left.rx_delay_base == right.rx_delay_base
        && left.ble_pin == right.ble_pin
        && left.advert_loc_policy == right.advert_loc_policy
        && left.buzzer_quiet == right.buzzer_quiet
        && left.gps_enabled == right.gps_enabled
        && left.gps_interval == right.gps_interval
        && left.autoadd_config == right.autoadd_config
        && left.rx_boosted_gain == right.rx_boosted_gain
        && left.client_repeat == right.client_repeat
        && left.path_hash_mode == right.path_hash_mode
        && left.autoadd_max_hops == right.autoadd_max_hops
        && std::memcmp(left.default_scope_name, right.default_scope_name, sizeof(left.default_scope_name)) == 0
        && std::memcmp(left.default_scope_key, right.default_scope_key, sizeof(left.default_scope_key)) == 0;
}

} // namespace

bool PiDonorDataStoreHost::onContactLoaded(const ContactInfo&) {
    return true;
}

bool PiDonorDataStoreHost::getContactForSave(uint32_t, ContactInfo&) {
    return false;
}

bool PiDonorDataStoreHost::onChannelLoaded(uint8_t, const ChannelDetails&) {
    return true;
}

bool PiDonorDataStoreHost::getChannelForSave(uint8_t, ChannelDetails&) {
    return false;
}

PiDonorDataStoreProbe::PiDonorDataStoreProbe()
    : state_{}, host_(), datastore_() {}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::bind(PiDonorHostContracts& contracts) {
    state_ = {};
    datastore_.reset();

    state_.datastore_host_ready = true;

    auto* secondary_fs = contracts.donor_secondary_filesystem();
    if (secondary_fs != nullptr) {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            *secondary_fs,
            contracts.donor_rtc_clock());
        state_.using_secondary_filesystem = true;
    } else {
        datastore_ = std::make_unique<DataStore>(
            contracts.donor_primary_filesystem(),
            contracts.donor_rtc_clock());
    }

    state_.datastore_constructed = datastore_ != nullptr;
    if (state_.datastore_constructed) {
        datastore_->begin();
        state_.begin_called = true;
        state_.blob_store_ready = contracts.donor_primary_filesystem().exists("/bl");

        contracts.donor_primary_filesystem().remove("/identity/_main.id");

        mesh::LocalIdentity saved_identity;
        mesh::LocalIdentity loaded_identity;

        state_.identity_missing_before_save = !datastore_->loadMainIdentity(loaded_identity);
        state_.identity_saved = datastore_->saveMainIdentity(saved_identity);
        state_.identity_file_ready = contracts.donor_primary_filesystem().exists("/identity/_main.id");
        state_.identity_loaded_after_save = datastore_->loadMainIdentity(loaded_identity);

        contracts.donor_primary_filesystem().remove("/new_prefs");
        contracts.donor_primary_filesystem().remove("/node_prefs");

        const NodePrefs saved_prefs = build_probe_prefs();
        NodePrefs loaded_prefs{};
        constexpr double saved_latitude = 51.5074;
        constexpr double saved_longitude = -0.1278;
        double loaded_latitude = 0.0;
        double loaded_longitude = 0.0;

        datastore_->savePrefs(saved_prefs, saved_latitude, saved_longitude);
        state_.prefs_saved = contracts.donor_primary_filesystem().exists("/new_prefs");
        state_.prefs_file_ready = state_.prefs_saved;
        datastore_->loadPrefs(loaded_prefs, loaded_latitude, loaded_longitude);
        state_.prefs_loaded = true;
        state_.prefs_roundtrip_ok = prefs_equal(saved_prefs, loaded_prefs)
            && loaded_latitude == saved_latitude
            && loaded_longitude == saved_longitude;
    }

    state_.probe_ready = state_.datastore_host_ready
        && state_.datastore_constructed
        && state_.begin_called
        && state_.blob_store_ready
        && state_.identity_missing_before_save
        && state_.identity_saved
        && state_.identity_file_ready
        && state_.identity_loaded_after_save
        && state_.prefs_saved
        && state_.prefs_file_ready
        && state_.prefs_loaded
        && state_.prefs_roundtrip_ok;
    return state_;
}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::state() const {
    return state_;
}

DataStore* PiDonorDataStoreProbe::datastore() {
    return datastore_.get();
}

} // namespace pi_port