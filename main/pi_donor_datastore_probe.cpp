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

ContactInfo build_probe_contact() {
    ContactInfo contact{};
    std::uint8_t pub_key[PUB_KEY_SIZE]{};
    for (std::size_t index = 0; index < PUB_KEY_SIZE; ++index) {
        pub_key[index] = static_cast<std::uint8_t>(index + 16U);
    }
    contact.id = mesh::Identity(pub_key);
    std::strcpy(contact.name, "probe-contact");
    contact.type = 1;
    contact.flags = 3;
    contact.out_path_len = 4;
    contact.shared_secret_valid = false;
    for (std::size_t index = 0; index < MAX_PATH_SIZE; ++index) {
        contact.out_path[index] = index < contact.out_path_len
            ? static_cast<std::uint8_t>(index + 1U)
            : 0U;
    }
    contact.last_advert_timestamp = 123456U;
    contact.lastmod = 654321U;
    contact.gps_lat = 51507400;
    contact.gps_lon = -127800;
    contact.sync_since = 42U;
    return contact;
}

bool contacts_equal(const ContactInfo& left, const ContactInfo& right) {
    return std::memcmp(left.id.pub_key, right.id.pub_key, PUB_KEY_SIZE) == 0
        && std::memcmp(left.name, right.name, sizeof(left.name)) == 0
        && left.type == right.type
        && left.flags == right.flags
        && left.out_path_len == right.out_path_len
        && std::memcmp(left.out_path, right.out_path, MAX_PATH_SIZE) == 0
        && left.last_advert_timestamp == right.last_advert_timestamp
        && left.lastmod == right.lastmod
        && left.gps_lat == right.gps_lat
        && left.gps_lon == right.gps_lon
        && left.sync_since == right.sync_since;
}

ChannelDetails build_probe_channel() {
    ChannelDetails channel{};
    std::strcpy(channel.name, "ops-room");
    for (std::size_t index = 0; index < PUB_KEY_SIZE; ++index) {
        channel.channel.secret[index] = static_cast<std::uint8_t>(index + 32U);
    }
    return channel;
}

bool channels_equal(const ChannelDetails& left, const ChannelDetails& right) {
    return std::memcmp(left.name, right.name, sizeof(left.name)) == 0
        && std::memcmp(left.channel.secret, right.channel.secret, PUB_KEY_SIZE) == 0;
}

} // namespace

PiDonorDataStoreHost::PiDonorDataStoreHost()
    : probe_contact_{},
      loaded_contact_{},
      probe_channel_{},
      loaded_channel_{},
      probe_contact_ready_(false),
      loaded_contact_ready_(false),
      probe_channel_ready_(false),
      loaded_channel_ready_(false) {}

void PiDonorDataStoreHost::set_probe_contact(const ContactInfo& contact) {
    probe_contact_ = contact;
    probe_contact_ready_ = true;
}

void PiDonorDataStoreHost::reset_loaded_contact() {
    loaded_contact_ = {};
    loaded_contact_ready_ = false;
}

bool PiDonorDataStoreHost::has_loaded_contact() const {
    return loaded_contact_ready_;
}

const ContactInfo& PiDonorDataStoreHost::loaded_contact() const {
    return loaded_contact_;
}

void PiDonorDataStoreHost::set_probe_channel(const ChannelDetails& channel) {
    probe_channel_ = channel;
    probe_channel_ready_ = true;
}

void PiDonorDataStoreHost::reset_loaded_channel() {
    loaded_channel_ = {};
    loaded_channel_ready_ = false;
}

bool PiDonorDataStoreHost::has_loaded_channel() const {
    return loaded_channel_ready_;
}

const ChannelDetails& PiDonorDataStoreHost::loaded_channel() const {
    return loaded_channel_;
}

bool PiDonorDataStoreHost::onContactLoaded(const ContactInfo& contact) {
    loaded_contact_ = contact;
    loaded_contact_ready_ = true;
    return false;
}

bool PiDonorDataStoreHost::getContactForSave(uint32_t idx, ContactInfo& contact) {
    if (!probe_contact_ready_ || idx != 0) {
        return false;
    }
    contact = probe_contact_;
    return true;
}

bool PiDonorDataStoreHost::onChannelLoaded(uint8_t, const ChannelDetails& channel) {
    loaded_channel_ = channel;
    loaded_channel_ready_ = true;
    return false;
}

bool PiDonorDataStoreHost::getChannelForSave(uint8_t channel_idx, ChannelDetails& channel) {
    if (!probe_channel_ready_ || channel_idx != 0) {
        return false;
    }
    channel = probe_channel_;
    return true;
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

        auto* contacts_fs = secondary_fs != nullptr ? secondary_fs : &contracts.donor_primary_filesystem();
        contacts_fs->remove("/contacts3");

        const ContactInfo saved_contact = build_probe_contact();
        host_.set_probe_contact(saved_contact);
        host_.reset_loaded_contact();

        datastore_->saveContacts(&host_);
        state_.contacts_saved = contacts_fs->exists("/contacts3");
        state_.contacts_file_ready = state_.contacts_saved;
        datastore_->loadContacts(&host_);
        state_.contacts_loaded = host_.has_loaded_contact();
        state_.contacts_roundtrip_ok = state_.contacts_loaded
            && contacts_equal(saved_contact, host_.loaded_contact());

        auto* channels_fs = secondary_fs != nullptr ? secondary_fs : &contracts.donor_primary_filesystem();
        channels_fs->remove("/channels2");

        const ChannelDetails saved_channel = build_probe_channel();
        host_.set_probe_channel(saved_channel);
        host_.reset_loaded_channel();

        datastore_->saveChannels(&host_);
        state_.channels_saved = channels_fs->exists("/channels2");
        state_.channels_file_ready = state_.channels_saved;
        datastore_->loadChannels(&host_);
        state_.channels_loaded = host_.has_loaded_channel();
        state_.channels_roundtrip_ok = state_.channels_loaded
            && channels_equal(saved_channel, host_.loaded_channel());
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
        && state_.prefs_roundtrip_ok
        && state_.contacts_saved
        && state_.contacts_file_ready
        && state_.contacts_loaded
        && state_.contacts_roundtrip_ok
        && state_.channels_saved
        && state_.channels_file_ready
        && state_.channels_loaded
        && state_.channels_roundtrip_ok;
    return state_;
}

const DonorDataStoreProbeState& PiDonorDataStoreProbe::state() const {
    return state_;
}

DataStore* PiDonorDataStoreProbe::datastore() {
    return datastore_.get();
}

} // namespace pi_port