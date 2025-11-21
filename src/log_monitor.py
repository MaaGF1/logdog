"""
Log monitoring system with state machine support
"""
import re
import time
import threading
import subprocess
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TextIO

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import WatchdogConfig, EntryNode
from notifier import WatchdogNotifier
from state_machine import WatchdogStateMachine, WatchdogState


class LogMonitor:
    """Log monitor with state machine support"""
    
    def __init__(self, config: WatchdogConfig):
        self.config = config
        self.notifier = WatchdogNotifier(config)
        
        # Monitoring state
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Log patterns for node detection
        # 修复：严格匹配 [pipeline_data.name=...] | enter
        self.node_patterns = {
            # 优先级最高：严格匹配执行进入点
            # 格式：[pipeline_data.name=节点名] | enter
            'start': re.compile(r'\[pipeline_data\.name=(.*?)\]\s*\|\s*enter', re.IGNORECASE),
            
            # 备用：如果日志中有显式的 complete (虽然你提供的日志里 leave 没带名字，但保留以防万一)
            'complete': re.compile(r'\[pipeline_data\.name=(.*?)\]\s*\|\s*complete', re.IGNORECASE),
            
            # 兼容旧格式或备用格式 (仅当上面匹配不到时使用)
            # 这里的正则排除了 list=[...] 和 result.name=... 这种干扰项
            'general': re.compile(r'\[(?:node_name|pipeline_data\.name)=(.*?)\](?!.*(?:list=|result\.name=))', re.IGNORECASE)
        }
        
        # File monitoring
        self.log_file: Optional[TextIO] = None
    
    def start_monitoring(self) -> bool:
        """Start log monitoring"""
        if self.is_running:
            print("Log monitor is already running")
            return False
        
        if not self._prepare_log_source():
            print("Failed to prepare log source")
            return False
        
        self.stop_event.clear()
        self.is_running = True
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="WatchdogLogMonitor"
        )
        self.monitor_thread.start()
        
        print("Watchdog log monitor started")
        return True
    
    def stop_monitoring(self) -> bool:
        """Stop log monitoring"""
        if not self.is_running:
            return False
        
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                print("Warning: Monitor thread did not stop gracefully")
        
        self._cleanup_log_source()
        self.is_running = False
        
        print("Watchdog log monitor stopped")
        return True
    
    def _prepare_log_source(self) -> bool:
        """Prepare log source for monitoring"""
        if self.config.log_file_path:
            try:
                if os.path.exists(self.config.log_file_path):
                    self.log_file = open(self.config.log_file_path, 'r', encoding='utf-8', errors='ignore')
                    self.log_file.seek(0, os.SEEK_END)
                    print(f"Monitoring log file: {self.config.log_file_path}")
                    return True
                else:
                    print(f"Log file does not exist: {self.config.log_file_path}")
                    return False
            except Exception as e:
                print(f"Failed to open log file: {e}")
                return False
        elif self.config.enable_stdout_capture:
            print("Stdout capture monitoring not yet implemented")
            return False
        else:
            print("No log source configured")
            return False
    
    def _cleanup_log_source(self):
        """Cleanup log source"""
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        print("Starting Watchdog monitor loop...")
        
        while not self.stop_event.wait(self.config.monitor_interval):
            try:
                new_lines = self._read_new_log_lines()
                
                if new_lines:
                    for line in new_lines:
                        self._process_log_line(line.strip())
                
                self._check_timeouts()
                
            except Exception as e:
                print(f"Monitor loop error: {e}")
                import traceback
                traceback.print_exc()
        
        print("Monitor loop ended")
    
    def _read_new_log_lines(self) -> List[str]:
        """Read new lines from log source with rotation detection"""
        if not self.log_file:
            return []
        
        lines = []
        try:
            current_pos = self.log_file.tell()
            current_size = os.fstat(self.log_file.fileno()).st_size
            
            if current_size < current_pos:
                print("[WARNING] Log file truncated detected, resetting pointer to beginning.")
                self.log_file.seek(0)
            
            content = self.log_file.read()
            
            if content:
                if not content.endswith('\n'):
                    last_newline = content.rfind('\n')
                    if last_newline != -1:
                        bytes_to_rewind = len(content) - (last_newline + 1)
                        self.log_file.seek(self.log_file.tell() - bytes_to_rewind)
                        content = content[:last_newline + 1]
                    else:
                        self.log_file.seek(self.log_file.tell() - len(content))
                        return []
                
                lines = [line for line in content.split('\n') if line.strip()]
                
        except Exception as e:
            print(f"Error reading log file: {e}")
            self._cleanup_log_source()
            self._prepare_log_source()
        
        return lines
    
    def _process_log_line(self, line: str):
        """Process a single log line"""
        if not line:
            return
        
        # 优化：如果行里不包含 pipeline_data.name 或 node_name，直接跳过，节省正则性能
        if 'pipeline_data.name' not in line and 'node_name' not in line:
            return

        node_name = None
        
        # 优先匹配 start ( | enter )
        match = self.node_patterns['start'].search(line)
        if match:
            node_name = match.group(1).strip()
        else:
            # 尝试匹配 complete
            match = self.node_patterns['complete'].search(line)
            if match:
                node_name = match.group(1).strip()
            else:
                # 最后尝试 general，但通常 start 已经足够
                match = self.node_patterns['general'].search(line)
                if match:
                    node_name = match.group(1).strip()
        
        if not node_name:
            return
        
        print(f"[DEBUG] Detected node execution: {node_name}")
        
        # Check if this is an entry node first
        entry_node = self.config.is_entry_node(node_name)
        if entry_node:
            self._handle_entry_node(entry_node, node_name, line)
            return
        
        # Check state machine rules
        self._check_state_machine_rules(node_name, line)
    
    def _handle_entry_node(self, entry: EntryNode, node_name: str, log_line: str):
        """Handle entry node detection"""
        print(f"[ENTRY] Entry node detected: {entry.name} ({node_name})")
        
        active_states = self.config.state_machine.get_active_states()
        
        if active_states:
            print(f"[ENTRY] Resetting {len(active_states)} active states due to entry node")
            for state_name, state in active_states.items():
                self.notifier.send_state_interrupted(state_name, state, node_name)
        
        self.config.state_machine.reset_all_states()
        self.notifier.send_entry_detected(entry.name, entry, node_name)
        self._check_state_machine_rules(node_name, log_line)
    
    def _check_state_machine_rules(self, node_name: str, log_line: str):
        """Check state machine rules"""
        for state_name, state in self.config.state_machine.states.items():
            if self.config.state_machine.activate_state(state_name, node_name):
                print(f"[STATE] State '{state_name}' triggered by node '{node_name}'")
                self.notifier.send_state_activated(state_name, state)
        
        for state_name, state in self.config.state_machine.get_active_states().items():
            result = self.config.state_machine.check_transition(state_name, node_name)
            if result:
                is_completed, message = result
                print(f"[STATE] {message}")
                if is_completed:
                    self.notifier.send_state_completed(state_name, state, node_name)
    
    def _check_timeouts(self):
        """Check for timeout conditions in state machine rules"""
        timeouts = self.config.state_machine.check_timeouts()
        for state_name, state, elapsed_ms in timeouts:
            print(f"[STATE] TIMEOUT: State '{state_name}' exceeded timeout (elapsed: {elapsed_ms}ms)")
            self.notifier.send_state_timeout(state_name, state, elapsed_ms)
    
    def get_status(self) -> Dict:
        """Get monitoring status"""
        active_states = list(self.config.state_machine.get_active_states().keys())
        return {
            'running': self.is_running,
            'total_state_rules': len(self.config.state_machine.states),
            'total_entry_nodes': len(self.config.entry_nodes),
            'total_completion_nodes': len(self.config.completion_nodes),
            'active_state_rules': len(active_states),
            'active_state_rule_names': active_states,
            'log_source': self.config.log_file_path or 'stdout capture',
            'notification_available': self.config.is_notification_configured()
        }
    
    def get_detailed_status(self) -> Dict:
        """Get detailed status including state machine details"""
        status = self.get_status()
        state_details = {}
        for state_name, state in self.config.state_machine.states.items():
            state_details[state_name] = self.config.state_machine.get_state_status(state_name)
        status['state_details'] = state_details
        
        entry_details = {}
        for entry_name, entry in self.config.entry_nodes.items():
            entry_details[entry_name] = {
                'name': entry.name,
                'node_name': entry.node_name,
                'description': entry.description
            }
        status['entry_details'] = entry_details

        completion_details = {}
        for comp_name, comp in self.config.completion_nodes.items():
            completion_details[comp_name] = {
                'name': comp.name,
                'node_name': comp.node_name,
                'description': comp.description
            }
        status['completion_details'] = completion_details
        
        return status

# Keep backward compatibility
LogMonitor = LogMonitor