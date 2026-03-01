#pragma once

// Capability mode descriptor structure as defined in PRD section 5.4.2
struct CapabilityMode {
    int capture_width;
    int capture_height;
    int capture_fps;
    const char* pixel_format_in;
    const char* pixel_format_out;
    bool zero_copy_supported;
    bool hdr_supported;
    const char* notes;
};

// Plugin capabilities structure, including an array of supported modes.
typedef struct {
    const char* plugin_id;
    int version;
    CapabilityMode supported_modes[];
    size_t mode_count;
} PluginCapabilities;