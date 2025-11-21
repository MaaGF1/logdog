"""
Notification system for watchdog alerts
"""
import requests
import json
from typing import Optional
from datetime import datetime

# Import constants for checking
from config import (
    NOTIFY_STATE_ACTIVATED, 
    NOTIFY_STATE_COMPLETED, 
    NOTIFY_STATE_TIMEOUT, 
    NOTIFY_STATE_INTERRUPTED, 
    NOTIFY_ENTRY_DETECTED
)

class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_message(self, message: str) -> bool:
        """Send message via Telegram"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(self.api_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API error: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False


class WeChatWorkNotifier:
    """WeChat Work notification handler"""
    
    def __init__(self, webhook_key: str):
        self.webhook_key = webhook_key
        self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
    
    def send_message(self, message: str) -> bool:
        """Send message via WeChat Work"""
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    return True
                else:
                    print(f"WeChat Work API error: {result}")
                    return False
            else:
                print(f"WeChat Work HTTP error: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"WeChat Work send error: {e}")
            return False


class WatchdogNotifier:
    """Unified notification manager for watchdog"""
    
    def __init__(self, config):
        self.config = config
        self._telegram_notifier = None
        self._wechat_notifier = None
    
    def _get_telegram_notifier(self) -> Optional[TelegramNotifier]:
        """Get Telegram notifier instance"""
        if self._telegram_notifier is None and self.config.bot_token and self.config.chat_id:
            self._telegram_notifier = TelegramNotifier(self.config.bot_token, self.config.chat_id)
        return self._telegram_notifier
    
    def _get_wechat_notifier(self) -> Optional[WeChatWorkNotifier]:
        """Get WeChat Work notifier instance"""
        if self._wechat_notifier is None and self.config.webhook_key:
            self._wechat_notifier = WeChatWorkNotifier(self.config.webhook_key)
        return self._wechat_notifier
    
    def send_notification(self, message: str) -> bool:
        """Send notification with fallback mechanism"""
        available_platforms = self.config.get_available_notifiers()
        
        if not available_platforms:
            # Only print warning if we actually intended to send something but couldn't
            # print("Warning: No notification platforms available")
            return False
        
        # Determine try order
        try_order = []
        default_platform = self.config.default_ext_notify
        
        if default_platform and default_platform in available_platforms:
            try_order.append(default_platform)
        
        for platform in available_platforms:
            if platform not in try_order:
                try_order.append(platform)
        
        # Try sending notification
        for platform in try_order:
            try:
                if platform == 'telegram':
                    notifier = self._get_telegram_notifier()
                    if notifier and notifier.send_message(message):
                        print(f"Watchdog notification sent via Telegram")
                        return True
                elif platform == 'wechat':
                    notifier = self._get_wechat_notifier()
                    if notifier and notifier.send_message(message):
                        print(f"Watchdog notification sent via WeChat Work")
                        return True
            except Exception as e:
                print(f"Failed to send via {platform}: {e}")
                continue
        
        print("Failed to send watchdog notification via all platforms")
        return False
    
    # Legacy methods for backward compatibility
    def send_timeout_alert(self, rule_name: str, rule, elapsed_ms: float) -> bool:
        """Send timeout alert notification (legacy support)"""
        if not self.config.should_notify(NOTIFY_STATE_TIMEOUT):
            return False

        message = (
            f"WATCHDOG TIMEOUT ALERT\n\n"
            f"Rule: {rule_name}\n"
            f"Description: {getattr(rule, 'description', 'N/A')}\n"
            f"Start Node: {getattr(rule, 'start_node', 'N/A')}\n"
            f"Expected End Node: {getattr(rule, 'end_node', 'N/A')}\n"
            f"Timeout Threshold: {getattr(rule, 'timeout_ms', 'N/A')}ms\n"
            f"Elapsed Time: {elapsed_ms:.1f}ms\n"
            f"Last Start: {getattr(rule, 'last_start_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_rule_activated(self, rule_name: str, rule) -> bool:
        """Send rule activation notification (legacy support)"""
        if not self.config.should_notify(NOTIFY_STATE_ACTIVATED):
            return False

        message = (
            f"WATCHDOG RULE ACTIVATED\n\n"
            f"Rule: {rule_name}\n"
            f"Description: {getattr(rule, 'description', 'N/A')}\n"
            f"Start Node: {getattr(rule, 'start_node', 'N/A')}\n"
            f"Timeout: {getattr(rule, 'timeout_ms', 'N/A')}ms\n"
            f"Activation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_rule_completed(self, rule_name: str, rule, elapsed_ms: float) -> bool:
        """Send rule completion notification (legacy support)"""
        if not self.config.should_notify(NOTIFY_STATE_COMPLETED):
            return False

        message = (
            f"WATCHDOG RULE COMPLETED\n\n"
            f"Rule: {rule_name}\n"
            f"End Node: {getattr(rule, 'end_node', 'N/A')}\n"
            f"Elapsed Time: {elapsed_ms:.1f}ms\n"
            f"Timeout Threshold: {getattr(rule, 'timeout_ms', 'N/A')}ms\n"
            f"Completion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)

    # New state machine notification methods
    def send_state_activated(self, state_name: str, state) -> bool:
        """Send state activation notification"""
        if not self.config.should_notify(NOTIFY_STATE_ACTIVATED):
            return False

        message = (
            f"WATCHDOG STATE ACTIVATED\n\n"
            f"State: {state_name}\n"
            f"Description: {getattr(state, 'description', 'N/A')}\n"
            f"Start Node: {getattr(state, 'start_node', 'N/A')}\n"
            f"Transitions: {len(getattr(state, 'transitions', []))}\n"
            f"Activation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)

    def send_state_completed(self, state_name: str, state, node_name: str) -> bool:
        """Send state completion notification"""
        if not self.config.should_notify(NOTIFY_STATE_COMPLETED):
            return False

        message = (
            f"WATCHDOG STATE COMPLETED\n\n"
            f"State: {state_name}\n"
            f"Start Node: {getattr(state, 'start_node', 'N/A')}\n"
            f"Completion Node: {node_name}\n"
            f"Description: {getattr(state, 'description', 'N/A')}\n"
            f"Completion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)

    def send_state_timeout(self, state_name: str, state, elapsed_ms: int) -> bool:
        """Send state timeout notification"""
        if not self.config.should_notify(NOTIFY_STATE_TIMEOUT):
            return False

        current_transition = None
        if hasattr(state, 'transitions') and hasattr(state, 'current_transition_index'):
            if state.current_transition_index < len(state.transitions):
                current_transition = state.transitions[state.current_transition_index]
        
        message = (
            f"WATCHDOG STATE TIMEOUT\n\n"
            f"State: {state_name}\n"
            f"Start Node: {getattr(state, 'start_node', 'N/A')}\n"
            f"Waiting For: {getattr(current_transition, 'target_node', 'Unknown') if current_transition else 'Unknown'}\n"
            f"Timeout Threshold: {getattr(current_transition, 'timeout_ms', 'Unknown') if current_transition else 'Unknown'}ms\n"
            f"Elapsed Time: {elapsed_ms}ms\n"
            f"Description: {getattr(state, 'description', 'N/A')}\n"
            f"Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_state_interrupted(self, state_name: str, state, entry_node: str) -> bool:
        """Send state interruption notification (when entry node resets states)"""
        if not self.config.should_notify(NOTIFY_STATE_INTERRUPTED):
            return False

        message = (
            f"WATCHDOG STATE INTERRUPTED\n\n"
            f"State: {state_name}\n"
            f"Start Node: {getattr(state, 'start_node', 'N/A')}\n"
            f"Interrupted By: {entry_node}\n"
            f"Description: {getattr(state, 'description', 'N/A')}\n"
            f"Interruption Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return self.send_notification(message)
    
    def send_entry_detected(self, entry_name: str, entry, node_name: str) -> bool:
        """Send entry node detection notification"""
        if not self.config.should_notify(NOTIFY_ENTRY_DETECTED):
            return False

        message = (
            f"WATCHDOG ENTRY NODE DETECTED\n\n"
            f"Entry: {entry_name}\n"
            f"Node: {node_name}\n"
            f"Description: {getattr(entry, 'description', 'N/A')}\n"
            f"Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"All active states have been reset."
        )
        
        return self.send_notification(message)