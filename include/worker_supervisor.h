#pragma once
#include <string>
#include <vector>
#include <map>

class WorkerSupervisor {
public:
    void startWorker(const std::string& pluginId);
    void stopWorker(const std::string& pluginId);
    bool isWorkerRunning(const std::string& pluginId);
    void sendIPCMessage(const std::string& pluginId, const std::string& message);
};