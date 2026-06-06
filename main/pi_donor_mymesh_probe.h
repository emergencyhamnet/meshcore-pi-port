#pragma once

#include <memory>

#include "../examples/companion_radio/MyMesh.h"
#include "pi_donor_datastore_probe.h"

namespace pi_port {

struct DonorMyMeshProbeState {
    bool mesh_constructed;
    bool begin_called;
    bool node_name_loaded;
    bool prefs_loaded;
    bool interface_started;
    bool serial_enabled_after_start;
    bool prefs_pointer_ready;
    bool command_loop_called;
    bool device_time_reply_ready;
    bool device_time_reply_valid;
    bool device_query_reply_ready;
    bool device_query_reply_valid;
    bool app_start_reply_ready;
    bool app_start_reply_valid;
    bool contacts_reply_ready;
    bool contacts_reply_valid;
    bool contacts_since_reply_ready;
    bool contacts_since_reply_valid;
    bool probe_ready;
};

class PiDonorMyMeshProbe {
public:
    PiDonorMyMeshProbe();

    const DonorMyMeshProbeState& bind(PiDonorRuntimeBridge& bridge, PiDonorHostContracts& contracts, PiDonorDataStoreProbe& datastore_probe);
    const DonorMyMeshProbeState& state() const;
    MyMesh* mesh();

private:
    class ProbeRadio final : public mesh::Radio {
    public:
        int recvRaw(uint8_t* bytes, int sz) override;
        uint32_t getEstAirtimeFor(int len_bytes) override;
        float packetScore(float snr, int packet_len) override;
        bool startSendRaw(const uint8_t* bytes, int len) override;
        bool isSendComplete() override;
        void onSendFinished() override;
        bool isInRecvMode() const override;
    };

    ProbeRadio radio_;
    StdRNG rng_;
    SimpleMeshTables tables_;
    DonorMyMeshProbeState state_;
    std::unique_ptr<MyMesh> mesh_;
};

} // namespace pi_port