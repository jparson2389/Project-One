// Implementation of capability matrix filtering

#include "capability_matrix_filtering.h"

// Function to filter supported modes based on device capabilities
std::vector<ModeDescriptor> filterSupportedModes(const DeviceCapabilities& deviceCaps, const std::vector<ModeDescriptor>& allModes) {
    std::vector<ModeDescriptor> supportedModes;
    for (const auto& mode : allModes) {
        if (deviceCaps.supports(mode.capture_width, mode.capture_height, mode.capture_fps)) {
            supportedModes.push_back(mode);
        }
    }
    return supportedModes;
}

// Additional functions and logic for capability matrix filtering can be added here