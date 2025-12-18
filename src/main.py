import sys
import os
import signal
import time

# Ensure we can find the C++ module (it will be in same dir after build)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import _logdog_core
except ImportError as e:
    print(f"CRITICAL: Could not import C++ core module: {e}")
    print("Ensure _logdog_core.pyd (Windows) or .so (Linux) is in the same directory.")
    sys.exit(1)

from config_loader import WatchdogConfig
from action_manager import ActionManager

# Map C++ Enum to String
EVENT_MAP = {
    _logdog_core.EventType.StateActivated: "StateActivated",
    _logdog_core.EventType.StateCompleted: "StateCompleted",
    _logdog_core.EventType.Timeout: "Timeout",
    _logdog_core.EventType.StateInterrupted: "StateInterrupted",
    _logdog_core.EventType.EntryDetected: "EntryDetected",
    _logdog_core.EventType.DebugLog: "DEBUG",
}

class App:
    def __init__(self):
        self.engine = None
        self.config = WatchdogConfig()
        self.action_mgr = None

    def run(self):
        conf_path = os.path.join(os.path.dirname(__file__), 'watchdog.conf')
        print(f"Loading config from {conf_path}")
        if not self.config.load(conf_path):
            print("Failed to load config.")
            return

        self.action_mgr = ActionManager(self.config)

        # Initialize C++ Engine
        log_path = self.config.log_file_path
        if not os.path.isabs(log_path):
            # Resolve relative to CWD or Config dir
            log_path = os.path.abspath(os.path.join(os.path.dirname(conf_path), log_path))

        print(f"Initializing Engine for: {log_path}")
        self.engine = _logdog_core.Engine(log_path, self.config.monitor_interval)

        # Configure Engine
        for name, start, trans, desc in self.config.states:
            self.engine.add_state_rule(name, start, trans, desc)
        
        self.engine.set_completion_nodes(self.config.completions)
        
        for name, node, desc in self.config.entries:
            self.engine.add_entry_node(name, node, desc)

        # Set Callback
        self.engine.set_callback(self.on_event)

        # Setup Signal Handling
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        print("Starting Watchdog...")
        self.engine.run() # Blocking call (releases GIL)

    def on_event(self, event_data):
        e_type_str = EVENT_MAP.get(event_data.type, "Unknown")

        # Special handling for C++ engine debug output (Not use cout, but output via python to avoid UTF8, GBK... issue)
        if e_type_str == "DEBUG":
            print(f"[DEBUG] Detected node execution: {event_data.node_name}")
            return

        print(f"[EVENT] {e_type_str} - {event_data.state_name}")
        
        context = {
            "state_name": event_data.state_name,
            "node_name": event_data.node_name,
            "description": event_data.description,
            "elapsed_ms": event_data.elapsed_ms
        }
        
        self.action_mgr.execute_actions(e_type_str, context)

    def stop(self, signum, frame):
        print("\nStopping...")
        if self.engine:
            self.engine.stop()

if __name__ == "__main__":
    App().run()