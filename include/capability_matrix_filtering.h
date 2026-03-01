#ifndef CAPABILITY_MATRIX_FILTERING_H
#define CAPABILITY_MATRIX_FILTERING_H

#include <vector>

struct ModeDescriptor {
    int capture_width;
    int capture_height;
    int capture_fps;
    std::string pixel_format_in;
    std::string pixel_format_out;
    bool zero_copy_supported;
    bool hdr_supported;
    std::vector<std::string> passthrough_supported_modes;
    std::string notes;
};

struct DeviceCapabilities {
    // Define device capabilities here
    bool supports(int width, int height, int fps) const;
};

std::vector<ModeDescriptor> filterSupportedModes(const DeviceCapabilities& deviceCaps, const std::vector<ModeDescriptor>& allModes);

#endif // CAPABILITY_MATRIX_FILTERING_H