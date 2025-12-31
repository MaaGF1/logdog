#include "state_machine.h"
#include <iostream>
#include <algorithm>
#include <limits>

namespace logdog {

StateMachine::StateMachine() 
    : is_active_(false), current_timeout_threshold_(-1) {}

void StateMachine::add_state_config(const StateConfig& config) {
    // Flatten the linear rule into graph edges
    // Rule: Start -> (T1, Node1) -> (T2, Node2) ...
    
    std::string current_source = config.start_node;
    
    for (const auto& trans : config.transitions) {
        const std::string& target = trans.first;
        int timeout = trans.second;

        GraphEdge edge;
        edge.target_node = target;
        edge.timeout_ms = timeout;
        edge.rule_name = config.name;
        edge.description = config.description;

        adjacency_list_[current_source].push_back(edge);

        // Move source forward
        current_source = target;
    }
}

void StateMachine::set_completion_nodes(const std::unordered_set<std::string>& nodes) {
    completion_nodes_ = nodes;
}

void StateMachine::add_entry_node(const std::string& node_name, const std::string& name, const std::string& desc) {
    entry_nodes_[node_name] = {name, desc};
}

void StateMachine::reset_state() {
    is_active_ = false;
    current_node_.clear();
    current_timeout_threshold_ = -1;
}

int StateMachine::calculate_min_timeout(const std::string& node_name) {
    if (adjacency_list_.find(node_name) == adjacency_list_.end()) {
        return -1; // No outgoing transitions, no timeout
    }
    
    const auto& edges = adjacency_list_[node_name];
    if (edges.empty()) return -1;

    int min_t = std::numeric_limits<int>::max();
    for (const auto& edge : edges) {
        if (edge.timeout_ms < min_t) {
            min_t = edge.timeout_ms;
        }
    }
    return min_t;
}

void StateMachine::transition_to(const std::string& node_name, const std::chrono::steady_clock::time_point& now) {
    current_node_ = node_name;
    last_transition_time_ = now;
    is_active_ = true;
    current_timeout_threshold_ = calculate_min_timeout(node_name);
}

std::vector<EventData> StateMachine::process_node(const std::string& node_name) {
    std::vector<EventData> events;
    auto now = std::chrono::steady_clock::now();

    // 1. Check Entry Nodes (Highest Priority - Hard Reset)
    if (entry_nodes_.count(node_name)) {
        if (is_active_) {
            events.push_back({EventType::StateInterrupted, 
                              "Global", 
                              node_name, 
                              "Interrupted by Entry: " + entry_nodes_[node_name].name, 
                              0});
        }
        
        // Reset and Start fresh
        reset_state();
        transition_to(node_name, now);
        
        events.push_back({EventType::EntryDetected, 
                          entry_nodes_[node_name].name, 
                          node_name, 
                          entry_nodes_[node_name].desc, 
                          0});
        return events;
    }

    // 2. If we are not tracking anything, check if this node starts any known path
    //    (In the graph model, this means checking if it exists as a key in adjacency_list_)
    if (!is_active_) {
        // If this node is a known source of transitions, we start tracking
        if (adjacency_list_.count(node_name)) {
            transition_to(node_name, now);
            events.push_back({EventType::StateActivated, 
                              "AutoStart", 
                              node_name, 
                              "Monitoring started from node", 
                              0});
        }
        return events;
    }

    // 3. We are active. Check if the new node is a valid transition from current_node_
    if (adjacency_list_.count(current_node_)) {
        const auto& edges = adjacency_list_[current_node_];
        
        for (const auto& edge : edges) {
            if (edge.target_node == node_name) {
                // MATCH FOUND!
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_transition_time_).count();
                
                // Log completion of previous step
                events.push_back({EventType::StateCompleted, 
                                  edge.rule_name, 
                                  current_node_, 
                                  "Transition to " + node_name, 
                                  (int)elapsed});

                // Move state
                transition_to(node_name, now);

                // Log activation of new step (context)
                events.push_back({EventType::StateActivated, 
                                  edge.rule_name, 
                                  node_name, 
                                  edge.description, 
                                  0});
                
                return events; // Only take the first matching transition
            }
        }
    }

    // 4. If no transition matched, we check if it's a Completion Node (End of line)
    if (completion_nodes_.count(node_name)) {
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_transition_time_).count();
        events.push_back({EventType::StateCompleted, 
                          "Final", 
                          node_name, 
                          "Reached completion node", 
                          (int)elapsed});
        reset_state();
    }

    return events;
}

std::vector<EventData> StateMachine::check_timeouts() {
    std::vector<EventData> events;
    
    if (!is_active_ || current_timeout_threshold_ < 0) {
        return events;
    }

    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_transition_time_).count();

    if (elapsed > current_timeout_threshold_) {
        // Construct a helpful message about what we were waiting for
        std::string waiting_for = "";
        if (adjacency_list_.count(current_node_)) {
            for (const auto& edge : adjacency_list_[current_node_]) {
                waiting_for += edge.target_node + " ";
            }
        }

        events.push_back({EventType::Timeout, 
                          "Watchdog", 
                          current_node_, 
                          "Timed out waiting for: [" + waiting_for + "]", 
                          (int)elapsed});
        
        // Reset state on timeout to prevent stale monitoring
        reset_state();
    }

    return events;
}

} // namespace logdog