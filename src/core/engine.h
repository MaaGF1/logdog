#pragma once
#include "state_machine.h"
#include "log_reader.h"
#include <functional>
#include <regex>
#include <atomic>

namespace logdog {

// Callback signature for Python
using EventCallback = std::function<void(const EventData&)>;

class Engine {
public:
    Engine(const std::string& log_path, double interval_sec);
    
    void add_state_rule(const std::string& name, const std::string& start_node, 
                       const std::vector<std::pair<std::string, int>>& transitions, 
                       const std::string& desc);
    
    void set_completion_nodes(const std::vector<std::string>& nodes);
    void add_entry_node(const std::string& key, const std::string& node_name, const std::string& desc);
    
    void set_callback(EventCallback cb);
    
    void run();
    void stop();

private:
    std::string log_path_;
    double interval_sec_;
    StateMachine sm_;
    EventCallback callback_;
    std::atomic<bool> running_;
    
    std::regex pattern_start_;
    std::regex pattern_complete_;
    std::regex pattern_general_;
};

}