#include <gtest/gtest.h>
#include "plugin_system.hpp"

using namespace aetherlink;

class MockPluginSystem : public PluginSystem {
public:
    void Initialize(const std::string& services) override {}
    void Start(const std::string& profile) override {}
    void Stop() override {}
    void Shutdown() override {}

    std::string GetCapabilities() const override { return "{}"; }
    std::vector<std::string> GetRequiredEntitlements() const override { return {}; }
    std::vector<std::string> GetRequiredDrivers() const override { return {}; }
    bool RequiresWorker() const override { return false; }
};

TEST(PluginSystemTest, Initialization) {
    MockPluginSystem plugin;
    plugin.Initialize("services");
}

TEST(PluginSystemTest, StartStop) {
    MockPluginSystem plugin;
    plugin.Start("profile");
    plugin.Stop();
}

TEST(PluginSystemTest, Shutdown) {
    MockPluginSystem plugin;
    plugin.Shutdown();
}

TEST(PluginSystemTest, Capabilities) {
    MockPluginSystem plugin;
    EXPECT_EQ(plugin.GetCapabilities(), "{}");
}

TEST(PluginSystemTest, Entitlements) {
    MockPluginSystem plugin;
    EXPECT_TRUE(plugin.GetRequiredEntitlements().empty());
}

TEST(PluginSystemTest, Drivers) {
    MockPluginSystem plugin;
    EXPECT_TRUE(plugin.GetRequiredDrivers().empty());
}

TEST(PluginSystemTest, WorkerRequirement) {
    MockPluginSystem plugin;
    EXPECT_FALSE(plugin.RequiresWorker());
}