// This file defines the C-ABI plugin lifecycle and capability contract.
// Frozen after Phase 0 completion.

#ifndef PLUGIN_SYSTEM_HPP
#define PLUGIN_SYSTEM_HPP

#include <cstdint>
#include <string>

struct Services;
struct Profile;

enum class PluginType {
    INPUT_PROVIDER,
    OUTPUT_PROVIDER,
    CAPTURE_PROVIDER,
    DISPLAY_PANEL,
    INFERENCE_ENGINE,
    SCRIPTING_ENGINE,
    REMOTE_PLAY_INTEGRATION,
    ONLINE_RESOURCES_CLIENT,
    ENVIRONMENT_MANAGER,
    ADMIN_DASHBOARD,
    BRIDGE_PLUGIN
};

struct PluginIdentity {
    std::string plugin_id;
    std::string name;
    std::string version;
    uint32_t api_version;
    PluginType plugin_type;
};

struct Capability {
    std::string name;
    std::string description;
};

struct PluginPolicy {
    std::vector<std::string> required_entitlements;
    std::vector<std::string> requires_drivers;
    bool requires_worker;
};

class IPlugin {
public:
    virtual ~IPlugin() = default;

    virtual PluginIdentity GetIdentity() const = 0;
    virtual void Initialize(Services* services) = 0;
    virtual void Start(Profile* profile) = 0;
    virtual void Stop() = 0;
    virtual void Shutdown() = 0;
    virtual std::vector<Capability> GetCapabilities() const = 0;
    virtual PluginPolicy GetPolicy() const = 0;
};

#endif // PLUGIN_SYSTEM_HPP