"""
Watchdog Configuration Management with State Machine Support
"""
import os
import re
import json
from typing import Dict, List, Optional, Tuple, Union, Set
from datetime import datetime

from state_machine import WatchdogStateMachine, WatchdogState, WatchdogTransition

# Notification Event Constants
NOTIFY_STATE_ACTIVATED = 'StateActivated'
NOTIFY_STATE_COMPLETED = 'StateCompleted'
NOTIFY_STATE_TIMEOUT = 'Timeout'
NOTIFY_STATE_INTERRUPTED = 'StateInterrupted'
NOTIFY_ENTRY_DETECTED = 'EntryDetected'

# Default enabled events if not specified
DEFAULT_NOTIFY_EVENTS = {
    NOTIFY_STATE_ACTIVATED,
    NOTIFY_STATE_COMPLETED,
    NOTIFY_STATE_TIMEOUT,
    NOTIFY_STATE_INTERRUPTED,
    NOTIFY_ENTRY_DETECTED
}

class EntryNode:
    def __init__(self, name: str, node_name: str, description: str = ""):
        self.name = name
        self.node_name = node_name
        self.description = description
    
    def __str__(self):
        return f"EntryNode({self.name}: {self.node_name})"

class CompletionNode:
    def __init__(self, name: str, node_name: str, description: str = ""):
        self.name = name
        self.node_name = node_name
        self.description = description

    def __str__(self):
        return f"CompletionNode({self.name}: {self.node_name})"

class WatchdogConfig:
    """Watchdog configuration manager with state machine support"""
    
    def __init__(self):
        self.state_machine = WatchdogStateMachine()
        self.entry_nodes: Dict[str, EntryNode] = {}
        self.completion_nodes: Dict[str, CompletionNode] = {}
        
        # 修复：默认正则同步为严格模式
        self.log_patterns = {
            'node_start': r'\[pipeline_data\.name=(.*?)\]\s*\|\s*enter',
            'node_complete': r'\[pipeline_data\.name=(.*?)\]\s*\|\s*complete',
        }
        
        self.bot_token = None
        self.chat_id = None
        self.webhook_key = None
        self.default_ext_notify = None
        
        # Set of events that should trigger a notification
        # Defaults to all events for backward compatibility
        self.notify_events: Set[str] = DEFAULT_NOTIFY_EVENTS.copy()
        self._custom_notify_configured = False
        
        self.log_file_path = None
        self.monitor_interval = 1.0
        self.enable_stdout_capture = False
        
    def load_config(self, config_path: str) -> bool:
        if not os.path.exists(config_path):
            print(f"Watchdog config file not found: {config_path}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                current_section = None
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1].lower()
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if current_section == 'notification':
                            self._parse_notification_config(key, value)
                        elif current_section == 'monitoring':
                            self._parse_monitoring_config(key, value)
                        elif current_section == 'states':
                            self._parse_state_config(key, value, line_num)
                        elif current_section == 'entries':
                            self._parse_entry_config(key, value, line_num)
                        elif current_section == 'completed':
                            self._parse_completed_config(key, value, line_num)
                        elif current_section == 'rules':
                            self._parse_legacy_as_state_config(key, value, line_num)
            
            completion_node_names = {c.node_name for c in self.completion_nodes.values()}
            self.state_machine.set_completion_nodes(completion_node_names)
            
            print(f"Loaded {len(self.state_machine.states)} state machine rules")
            print(f"Loaded {len(self.entry_nodes)} entry nodes")
            print(f"Loaded {len(self.completion_nodes)} completion nodes")
            
            if self._custom_notify_configured:
                print(f"Notification filter enabled: {', '.join(self.notify_events)}")
            else:
                print("Notification filter: Default (All events)")
                
            return True
            
        except Exception as e:
            print(f"Failed to load watchdog config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_notification_config(self, key: str, value: str):
        if key == 'Bot_Token':
            self.bot_token = value if value else None
        elif key == 'Chat_ID':
            self.chat_id = value if value else None
        elif key == 'Webhook_Key':
            self.webhook_key = value if value else None
        elif key == 'Default_ExtNotify':
            self.default_ext_notify = value.lower() if value else None
        elif key == 'NotifyWhen':
            self._parse_notify_when(value)

    def _parse_notify_when(self, value: str):
        """Parse the NotifyWhen={...} configuration"""
        if not value:
            return
        
        # Remove braces if present
        if value.startswith('{') and value.endswith('}'):
            value = value[1:-1]
        
        # Split by comma
        parts = [p.strip() for p in value.split(',')]
        if not parts:
            return
            
        # Reset to empty set since user provided specific config
        self.notify_events = set()
        self._custom_notify_configured = True
        
        valid_events = {
            NOTIFY_STATE_ACTIVATED.lower(): NOTIFY_STATE_ACTIVATED,
            NOTIFY_STATE_COMPLETED.lower(): NOTIFY_STATE_COMPLETED,
            NOTIFY_STATE_TIMEOUT.lower(): NOTIFY_STATE_TIMEOUT,
            NOTIFY_STATE_INTERRUPTED.lower(): NOTIFY_STATE_INTERRUPTED,
            NOTIFY_ENTRY_DETECTED.lower(): NOTIFY_ENTRY_DETECTED
        }
        
        for part in parts:
            # Handle potential legacy "RuleActivated" etc mapping if needed, 
            # but for now strictly follow the requested format
            part_lower = part.lower()
            if part_lower in valid_events:
                self.notify_events.add(valid_events[part_lower])
            else:
                print(f"Warning: Unknown notification event type: {part}")

    def _parse_monitoring_config(self, key: str, value: str):
        if key == 'Log_File_Path':
            self.log_file_path = value if value else None
        elif key == 'Monitor_Interval':
            try:
                self.monitor_interval = float(value)
                if self.monitor_interval <= 0:
                    self.monitor_interval = 1.0
            except ValueError:
                print(f"Invalid Monitor_Interval: {value}, using default 1.0")
        elif key == 'Enable_Stdout_Capture':
            self.enable_stdout_capture = value.lower() in ['true', '1', 'yes', 'on']
    
    def _parse_legacy_as_state_config(self, key: str, value: str, line_num: int):
        try:
            if value.startswith('{') and value.endswith('}'):
                value = value[1:-1]
            parts = [part.strip() for part in value.split(',')]
            if len(parts) < 3:
                return
            start_node = parts[0]
            timeout_ms = int(parts[1])
            end_node = parts[2]
            description = parts[3] if len(parts) > 3 else ""
            transition = WatchdogTransition(end_node, timeout_ms, f"Transition to {end_node}")
            state = WatchdogState(name=key, start_node=start_node, transitions=[transition], description=description)
            self.state_machine.add_state(state)
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse legacy rule at line {line_num}: {key}={value}, error: {e}")
    
    def _parse_state_config(self, key: str, value: str, line_num: int):
        try:
            if value.startswith('{') and value.endswith('}'):
                value = value[1:-1]
            parts = [part.strip() for part in value.split(',')]
            if len(parts) < 3:
                return
            start_node = parts[0]
            transitions = []
            description = ""
            i = 1
            while i < len(parts):
                try:
                    timeout_ms = int(parts[i])
                    if i + 1 < len(parts):
                        end_node = parts[i + 1]
                        has_next_timeout = False
                        if i + 2 < len(parts):
                            try:
                                int(parts[i + 2])
                                has_next_timeout = True
                            except ValueError:
                                pass
                        transitions.append(WatchdogTransition(end_node, timeout_ms, f"Transition to {end_node}"))
                        i += 2
                        if not has_next_timeout and i < len(parts):
                            description = ', '.join(parts[i:])
                            break
                    else:
                        break
                except ValueError:
                    description = ', '.join(parts[i:])
                    break
            if not transitions:
                return
            state = WatchdogState(name=key, start_node=start_node, transitions=transitions, description=description)
            self.state_machine.add_state(state)
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse state at line {line_num}: {key}={value}, error: {e}")
    
    def _parse_entry_config(self, key: str, value: str, line_num: int):
        try:
            if value.startswith('{') and value.endswith('}'):
                value = value[1:-1]
            parts = [part.strip() for part in value.split(',')]
            if len(parts) < 1:
                return
            node_name = parts[0]
            description = parts[1] if len(parts) > 1 else ""
            entry = EntryNode(key, node_name, description)
            self.entry_nodes[key] = entry
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse entry at line {line_num}: {key}={value}, error: {e}")

    def _parse_completed_config(self, key: str, value: str, line_num: int):
        try:
            if value.startswith('{') and value.endswith('}'):
                value = value[1:-1]
            parts = [part.strip() for part in value.split(',')]
            if len(parts) < 1:
                return
            node_name = parts[0]
            description = parts[1] if len(parts) > 1 else ""
            completion = CompletionNode(key, node_name, description)
            self.completion_nodes[key] = completion
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse completed at line {line_num}: {key}={value}, error: {e}")
    
    def get_state(self, name: str) -> Optional[WatchdogState]:
        return self.state_machine.states.get(name)
    
    def get_entry(self, name: str) -> Optional[EntryNode]:
        return self.entry_nodes.get(name)
    
    def get_completion(self, name: str) -> Optional[CompletionNode]:
        return self.completion_nodes.get(name)
    
    def is_entry_node(self, node_name: str) -> Optional[EntryNode]:
        for entry in self.entry_nodes.values():
            if entry.node_name == node_name:
                return entry
        return None
    
    def is_completion_node(self, node_name: str) -> Optional[CompletionNode]:
        for comp in self.completion_nodes.values():
            if comp.node_name == node_name:
                return comp
        return None
    
    def is_notification_configured(self) -> bool:
        return (self.bot_token and self.chat_id) or (self.webhook_key is not None)
    
    def get_available_notifiers(self) -> List[str]:
        available = []
        if self.bot_token and self.chat_id:
            available.append('telegram')
        if self.webhook_key:
            available.append('wechat')
        return available

    def should_notify(self, event_type: str) -> bool:
        """Check if the specific event type is enabled for notification"""
        return event_type in self.notify_events

watchdog_config = WatchdogConfig()

def load_watchdog_config(config_path: str) -> bool:
    return watchdog_config.load_config(config_path)

def get_watchdog_config() -> WatchdogConfig:
    return watchdog_config