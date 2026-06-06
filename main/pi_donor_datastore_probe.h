#pragma once

#include <memory>

#include "../examples/companion_radio/DataStore.h"
#include "pi_donor_host_contracts.h"

namespace pi_port {

struct DonorDataStoreProbeState {
    bool datastore_host_ready;
    bool datastore_constructed;
    bool using_secondary_filesystem;
    bool begin_called;
    bool blob_store_ready;
    bool identity_missing_before_save;
    bool identity_saved;
    bool identity_file_ready;
    bool identity_loaded_after_save;
    bool prefs_saved;
    bool prefs_file_ready;
    bool prefs_loaded;
    bool prefs_roundtrip_ok;
    bool probe_ready;
};

class PiDonorDataStoreHost final : public DataStoreHost {
public:
    bool onContactLoaded(const ContactInfo& contact) override;
    bool getContactForSave(uint32_t idx, ContactInfo& contact) override;
    bool onChannelLoaded(uint8_t channel_idx, const ChannelDetails& ch) override;
    bool getChannelForSave(uint8_t channel_idx, ChannelDetails& ch) override;
};

class PiDonorDataStoreProbe {
public:
    PiDonorDataStoreProbe();

    const DonorDataStoreProbeState& bind(PiDonorHostContracts& contracts);
    const DonorDataStoreProbeState& state() const;
    DataStore* datastore();

private:
    DonorDataStoreProbeState state_;
    PiDonorDataStoreHost host_;
    std::unique_ptr<DataStore> datastore_;
};

} // namespace pi_port