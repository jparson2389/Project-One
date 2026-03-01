#pragma once

#include <string>
#include <vector>

namespace aetherlink {

class PluginSystem {
public:
    virtual ~PluginSystem() = default;

    virtual void Initialize(const std::string& services) = 0;
    virtual void Start(const std::string& profile) = 0;
    virtual void Stop() = 0;
    virtual void Shutdown() = 0;

    virtual std::string GetCapabilities() const = 0;
    virtual std::vector<std::string> GetRequiredEntitlements() const = 0;
    virtual std::vector<std::string> GetRequiredDrivers() const = 0;
    virtual bool RequiresWorker() const = 0;
};

} // namespace aetherlink