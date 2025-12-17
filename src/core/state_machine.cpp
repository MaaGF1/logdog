#include "state_machine.h"
#include <iostream>

namespace logdog {

StateMachine::StateMachine() {}

void StateMachine::add_state_config(const StateConfig& config) {
    configs_[config.name] = config;
}

void StateMachine::set_completion_nodes(const std::unordered_set<std::string>& nodes) {
    completion_nodes_ = nodes;
}

void StateMachine::add_entry_node(const std::string& node_name, const std::string& name, const std::string& desc) {
    entry_nodes_[node_name] = {name, desc};
}

std::vector<EventData> StateMachine::process_node(const std::string& node_name) {
    std::vector<EventData> events;
    auto now = std::chrono::steady_clock::now();

    // 1. Check Entry Nodes (High Priority)
    if (entry_nodes_.count(node_name)) {
        if (!active_states_.empty()) {
            for (const auto& pair : active_states_) {
                events.push_back({EventType::StateInterrupted, pair.first, node_name, configs_[pair.first].description, 0});
            }
            active_states_.clear();
        }
        events.push_back({EventType::EntryDetected, entry_nodes_[node_name].name, node_name, entry_nodes_[node_name].desc, 0});
    }

    // 2. Check New Activations
    for (const auto& pair : configs_) {
        const auto& config = pair.second;
        if (config.start_node == node_name) {
            ActiveState active;
            active.name = config.name;
            active.current_transition_idx = 0;
            active.last_activation = now;
            active_states_[config.name] = active;
            
            events.push_back({EventType::StateActivated, config.name, node_name, config.description, 0});
        }
    }

    // 3. Check Transitions for Active States
    // We iterate a copy of keys to safely modify the map
    std::vector<std::string> active_names;
    for(const auto& pair : active_states_) active_names.push_back(pair.first);

    for (const auto& name : active_names) {
        if (active_states_.find(name) == active_states_.end()) continue; // Already removed

        auto& active = active_states_[name];
        const auto& config = configs_[name];

        if (active.current_transition_idx >= config.transitions.size()) continue;

        const auto& transition = config.transitions[active.current_transition_idx];

        if (transition.target_node == node_name) {
            // Transition matched
            bool is_last = (active.current_transition_idx == config.transitions.size() - 1);
            bool is_explicit_complete = (completion_nodes_.count(node_name) > 0);
            bool is_loop = (node_name == config.start_node);

            if (is_last) {
                if (is_explicit_complete || !is_loop) {
                    // Completed
                    events.push_back({EventType::StateCompleted, name, node_name, config.description, 0});
                    active_states_.erase(name);
                } else {
                    // Loop reset
                    active.current_transition_idx = 0;
                    active.last_activation = now;
                }
            } else {
                // Next step
                active.current_transition_idx++;
                active.last_activation = now;
            }
        }
    }

    return events;
}

std::vector<EventData> StateMachine::check_timeouts() {
    std::vector<EventData> events;
    auto now = std::chrono::steady_clock::now();
    std::vector<std::string> to_remove;

    for (auto& pair : active_states_) {
        const auto& name = pair.first;
        auto& active = pair.second;
        const auto& config = configs_[name];

        if (active.current_transition_idx < config.transitions.size()) {
            int timeout_threshold = config.transitions[active.current_transition_idx].timeout_ms;
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - active.last_activation).count();

            if (elapsed > timeout_threshold) {
                events.push_back({EventType::Timeout, name, "TIMEOUT", config.description, (int)elapsed});
                to_remove.push_back(name);
            }
        }
    }

    for (const auto& name : to_remove) {
        active_states_.erase(name);
    }

    return events;
}

} // namespace logdog