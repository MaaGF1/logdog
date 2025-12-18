"""
MaaFramework Watchdog - Main Entry Point (Hybrid C++/Python)
Independent log-based watchdog for monitoring MaaFw agent execution
"""
import os
import sys
import time
import signal
import argparse
from datetime import datetime

# Ensure we can find the C++ module (it will be in same dir after build)
# This allows running from source or from built distribution
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    import _logdog_core
except ImportError as e:
    print(f"CRITICAL: Could not import C++ core module: {e}")
    print(f"Search path: {sys.path}")
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

def print_logo():
    """
    Prints the Dinergate(Dandelion) (Girls' Frontline) ASCII art.
    """
    logo = r"""
              .=====================.
             /|                     |\
            | |  Dandelion Service  | |
            | |                     | |
            |  \___________________/  |
             \_______________________/
                     \      /
                      \    /
                 .-----`--'-----.
                / .------------. \
               / /    .----.    \ \
              | |    /  ()  \    | |
              | |   |   __   |   | |
               \ \   \      /   / /
                \ '------------' /
                 \              /
                 /`.__________.'\
                /   /        \   \
               ^   ^          ^   ^
    """
    print(logo)

class WatchdogService:
    """Main watchdog service wrapper around C++ Engine"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = WatchdogConfig()
        self.action_mgr = None
        self.engine = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _get_default_config_path(self) -> str:
        """Get default config file path"""
        return os.path.join(current_dir, 'watchdog.conf')
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown()
    
    def initialize(self) -> bool:
        """Initialize watchdog service (Load Config & Prepare)"""
        print("Initializing MaaFramework Watchdog...")
        print(f"Config file: {self.config_path}")
        
        # Load configuration
        if not self.config.load(self.config_path):
            print("Failed to load configuration")
            return False
        
        self.action_mgr = ActionManager(self.config)
        
        # Validate configuration
        if not self.config.states:
            print("No watchdog states configured")
            return False
        
        available_notifiers = self.config.get_available_notifiers()
        if not available_notifiers:
            print("Warning: No notification platforms configured")
        else:
            print(f"Notification platforms: {', '.join(available_notifiers)}")
            
        print("Watchdog service initialized successfully")
        return True

    def _setup_engine(self) -> bool:
        """Setup the C++ Engine instance"""
        log_path = self.config.log_file_path
        if not os.path.isabs(log_path):
            # Resolve relative to Config file location
            base_dir = os.path.dirname(self.config_path)
            log_path = os.path.abspath(os.path.join(base_dir, log_path))

        print(f"Target Log File: {log_path}")
        
        try:
            self.engine = _logdog_core.Engine(log_path, self.config.monitor_interval)

            # Configure Engine
            for name, start, trans, desc in self.config.states:
                self.engine.add_state_rule(name, start, trans, desc)
            
            self.engine.set_completion_nodes(self.config.completions)
            
            for name, node, desc in self.config.entries:
                self.engine.add_entry_node(name, node, desc)

            # Set Callback
            self.engine.set_callback(self.on_event)
            return True
        except Exception as e:
            print(f"Failed to create C++ Engine: {e}")
            return False

    def on_event(self, event_data):
        """Callback from C++ Engine"""
        e_type_str = EVENT_MAP.get(event_data.type, "Unknown")

        # Special handling for C++ engine debug output
        if e_type_str == "DEBUG":
            print(f"[DEBUG] {event_data.node_name}")
            return

        print(f"[EVENT] {e_type_str} - {event_data.state_name}")
        
        context = {
            "state_name": event_data.state_name,
            "node_name": event_data.node_name,
            "description": event_data.description,
            "elapsed_ms": event_data.elapsed_ms
        }
        
        self.action_mgr.execute_actions(e_type_str, context)
    
    def run(self) -> bool:
        """Run watchdog service (blocking)"""
        if not self._setup_engine():
            return False

        self.running = True
        
        # 1. Print Configuration Summary
        self.print_config_summary()
        
        # 2. Print Logo
        print_logo()
        
        # 3. Start Engine
        print(f"Starting C++ Engine at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop")
        print("-" * 60)
        
        try:
            # Blocking call (releases GIL internally in C++)
            self.engine.run() 
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        except Exception as e:
            print(f"Runtime error: {e}")
        finally:
            self.shutdown()
        
        return True
    
    def shutdown(self):
        """Shutdown watchdog service"""
        if not self.running:
            return
        
        print("Shutting down watchdog service...")
        if self.engine:
            self.engine.stop()
        
        self.running = False
        print("Watchdog service stopped")

    def print_config_summary(self):
        """Print summary of loaded configuration"""
        print("\n=== Configuration Summary ===")
        print(f"Total Rules: {len(self.config.states)}")
        print(f"Total Entries: {len(self.config.entries)}")
        print(f"Total Completions: {len(self.config.completions)}")
        
        print("\n[Loaded Rules]")
        for name, start, trans, desc in self.config.states:
            print(f"  - {name}: {desc}")
            print(f"    Start: {start}")
            # Format transitions nicely
            t_str = " -> ".join([f"{t[0]}({t[1]}ms)" for t in trans])
            print(f"    Path:  {t_str}")

        print("\n[Entry Points]")
        for name, node, desc in self.config.entries:
            print(f"  - {name}: {node} ({desc})")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='MaaFramework Watchdog Service (Hybrid)')
    parser.add_argument('--config', '-c', type=str, help='Path to configuration file')
    parser.add_argument('--status', action='store_true', help='Show loaded configuration and exit')
    
    args = parser.parse_args()
    
    # Create service instance
    service = WatchdogService(args.config)
    
    # Initialize
    if not service.initialize():
        sys.exit(1)
    
    # Handle status requests (Static config info only for hybrid mode)
    if args.status:
        service.print_config_summary()
        sys.exit(0)
    
    # Run service
    success = service.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()