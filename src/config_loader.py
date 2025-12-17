import os
from typing import Set, Dict, List

class WatchdogConfig:
    def __init__(self):
        self.log_file_path = ""
        self.monitor_interval = 1.0
        self.bot_token = None
        self.chat_id = None
        self.webhook_key = None
        self.default_ext_notify = None
        self.notify_events: Set[str] = {"Timeout", "StateInterrupted"} # Default
        
        # Raw data for C++ engine
        self.states = [] # list of tuples
        self.entries = []
        self.completions = []

    def load(self, path):
        if not os.path.exists(path): return False
        
        current_section = None
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].lower()
                    continue
                
                if '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip()
                    self._parse(current_section, k, v)
        return True

    def _parse(self, section, k, v):
        if section == 'notification':
            if k == 'Bot_Token': self.bot_token = v
            elif k == 'Chat_ID': self.chat_id = v
            elif k == 'Webhook_Key': self.webhook_key = v
            elif k == 'Default_ExtNotify': self.default_ext_notify = v
            elif k == 'NotifyWhen':
                v = v.replace('{','').replace('}','')
                self.notify_events = {x.strip() for x in v.split(',') if x.strip()}
        
        elif section == 'monitoring':
            if k == 'Log_File_Path': self.log_file_path = v
            elif k == 'Monitor_Interval': self.monitor_interval = float(v)
            
        elif section == 'states':
            # Parse: Name={Start, T1, End1, ... Desc}
            val = v.replace('{','').replace('}','')
            parts = [p.strip() for p in val.split(',')]
            if len(parts) >= 3:
                start = parts[0]
                trans = []
                idx = 1
                desc = ""
                while idx < len(parts):
                    try:
                        t_ms = int(parts[idx])
                        if idx+1 < len(parts):
                            target = parts[idx+1]
                            trans.append((target, t_ms))
                            idx += 2
                        else: break
                    except ValueError:
                        desc = ", ".join(parts[idx:])
                        break
                self.states.append((k, start, trans, desc))
                
        elif section == 'entries':
            val = v.replace('{','').replace('}','')
            parts = [p.strip() for p in val.split(',')]
            desc = parts[1] if len(parts) > 1 else ""
            self.entries.append((k, parts[0], desc))
            
        elif section == 'completed':
            val = v.replace('{','').replace('}','')
            parts = [p.strip() for p in val.split(',')]
            self.completions.append(parts[0])

    def should_notify(self, event_type):
        return event_type in self.notify_events

    def get_available_notifiers(self):
        res = []
        if self.bot_token: res.append('telegram')
        if self.webhook_key: res.append('wechat')
        return res