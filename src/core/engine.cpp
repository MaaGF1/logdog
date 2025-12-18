#include "engine.h"
#include <thread>
#include <iostream>

namespace logdog {

Engine::Engine(const std::string& log_path, double interval_sec) 
    : log_path_(log_path), interval_sec_(interval_sec), running_(false) {
    
    // Compile regex once
    pattern_start_ = std::regex(R"(\[pipeline_data\.name=(.*?)\]\s*\|\s*enter)", std::regex::icase | std::regex::optimize);
    pattern_complete_ = std::regex(R"(\[pipeline_data\.name=(.*?)\]\s*\|\s*complete)", std::regex::icase | std::regex::optimize);
    pattern_general_ = std::regex(R"(\[(?:node_name|pipeline_data\.name)=(.*?)\](?!.*(?:list=|result\.name=)))", std::regex::icase | std::regex::optimize);
}

void Engine::add_state_rule(const std::string& name, const std::string& start_node, 
                           const std::vector<std::pair<std::string, int>>& trans_pairs, 
                           const std::string& desc) {
    StateConfig config;
    config.name = name;
    config.start_node = start_node;
    config.description = desc;
    
    for (const auto& p : trans_pairs) {
        config.transitions.push_back({p.first, p.second});
    }
    sm_.add_state_config(config);
}

void Engine::set_completion_nodes(const std::vector<std::string>& nodes) {
    std::unordered_set<std::string> s(nodes.begin(), nodes.end());
    sm_.set_completion_nodes(s);
}

void Engine::add_entry_node(const std::string& key, const std::string& node_name, const std::string& desc) {
    sm_.add_entry_node(node_name, key, desc);
}

void Engine::set_callback(EventCallback cb) {
    callback_ = cb;
}

void Engine::stop() {
    running_ = false;
    cv_.notify_all();
}

void Engine::run() {
    LogReader reader(log_path_);
    if (!reader.open()) {
        std::cerr << "Failed to open log file: " << log_path_ << std::endl;
        return;
    }
    
    running_ = true;
    std::cout << "C++ Engine started. Monitoring: " << log_path_ << std::endl;

    while (running_) {
        // 1. Read Lines
        auto lines = reader.read_new_lines();
        
        for (const auto& line : lines) {

            // std::cout << "[RAW] " << line << std::endl; 

            // Quick filter
            if (line.find("pipeline_data.name") == std::string::npos && 
                line.find("node_name") == std::string::npos) {
                continue;
            }

            std::smatch match;
            std::string node_name;
            
            if (std::regex_search(line, match, pattern_start_) && match.size() > 1) {
                node_name = match[1].str();
            } else if (std::regex_search(line, match, pattern_complete_) && match.size() > 1) {
                node_name = match[1].str();
            } else if (std::regex_search(line, match, pattern_general_) && match.size() > 1) {
                node_name = match[1].str();
            }
            
            if (!node_name.empty()) {
                // Trim whitespace
                node_name.erase(0, node_name.find_first_not_of(" \t\r\n"));
                node_name.erase(node_name.find_last_not_of(" \t\r\n") + 1);

                // For Debug
                // std::cout << "[DEBUG] Detected node execution: " << node_name << std::endl;

                if (callback_)
                {
                    // Send a Debug Event
                    EventData debug_evt;
                    debug_evt.type = EventType::EngineLog;
                    debug_evt.node_name = node_name; 
                    debug_evt.description = "Node Detected: ";
                    debug_evt.elapsed_ms = 0;
                    callback_(debug_evt);
                }

                auto events = sm_.process_node(node_name);
                if (callback_) {
                    for (const auto& e : events) callback_(e);
                }
            }
        }

        // 2. Check Timeouts
        auto timeouts = sm_.check_timeouts();
        if (callback_) {
            for (const auto& e : timeouts) callback_(e);
        }

        // 3. Sleep
        std::unique_lock<std::mutex> lk(cv_m_);
        cv_.wait_for(lk, std::chrono::milliseconds(static_cast<int>(interval_sec_ * 1000)), [this]{
            return !running_; 
        });
    }
    
    reader.close();
    std::cout << "C++ Engine stopped." << std::endl;
}

}