#ifndef PLUGIN_SYSTEM_HPP
#define PLUGIN_SYSTEM_HPP

#include <string>
#include <vector>

// Forward declarations (replace with actual includes as needed)
class Services;
class Profile;

// Plugin Lifecycle Methods
typealias InitializeFn = void (*)(Services*);
struct PluginLifecycle {
    InitializeFn initialize;
    typealias StartFn = void (*)(Profile*);
    StartFn start;
    typealias StopFn = void (*); 
    StopFn stop;
    typealias ShutdownFn = void (*);
    ShutdownFn shutdown;
};

// Plugin Capabilities (example - expand as needed)
struct Capability {
    std::string name;
    std::string version;
}

//Plugin Identity
struct PluginIdentity{
  std::string plugin_id;
  std::string name;
  std::string version;
  std::string api_version;
  std::string plugin_type;
};

// Plugin Policy (example - expand as needed)
struct PluginPolicy {
    std::vector<std::string> required_entitlements;
    std::vector<std::string> requires_drivers;
    bool requires_worker;
};

//Plugin Capabilities Function
typealias GetCapabilitiesFn = std::vector<Capability>* (*)(void);

struct PluginExport {
  PluginIdentity identity;
  PluginLifecycle lifecycle;
  GetCapabilitiesFn get_capabilities;
  PluginPolicy policy;
};

#endif // PLUGIN_SYSTEM_HPP