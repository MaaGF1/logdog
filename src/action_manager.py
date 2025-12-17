import requests
import json
import os
import subprocess
import platform

class ActionManager:
    def __init__(self, config):
        self.config = config
        
    def execute_actions(self, event_type, context):
        """
        Execute actions configured for this event type.
        context: dict containing state_name, description, etc.
        """
        # Check if we should act on this event
        if not self.config.should_notify(event_type):
            return

        # Get actions (could be extended to be per-rule in future)
        # For now, we use the global notification config + potential extensions
        
        # 1. Notification Actions
        self._handle_notifications(event_type, context)
        
        # 2. OS Actions (Example: Shutdown on Timeout)
        if event_type == 'Timeout':
            # This is where you could read a config like "TimeoutAction=cmd:shutdown /s /t 60"
            pass

    def _handle_notifications(self, event_type, context):
        msg = self._format_message(event_type, context)
        
        platforms = self.config.get_available_notifiers()
        default = self.config.default_ext_notify
        
        # Sort to try default first
        if default in platforms:
            platforms.remove(default)
            platforms.insert(0, default)
            
        for p in platforms:
            if p == 'telegram':
                if self._send_telegram(msg): return
            elif p == 'wechat':
                if self._send_wechat(msg): return

    def _format_message(self, event_type, ctx):
        # Simplified formatter
        lines = [f"WATCHDOG EVENT: {event_type}"]
        for k, v in ctx.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def _send_telegram(self, msg):
        try:
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
            payload = {'chat_id': self.config.chat_id, 'text': msg}
            requests.post(url, data=payload, timeout=5)
            return True
        except Exception as e:
            print(f"Telegram failed: {e}")
            return False

    def _send_wechat(self, msg):
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.config.webhook_key}"
            payload = {"msgtype": "text", "text": {"content": msg}}
            requests.post(url, json=payload, timeout=5)
            return True
        except Exception as e:
            print(f"WeChat failed: {e}")
            return False