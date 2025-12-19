# Add these imports at the top
from datetime import datetime, timezone, timedelta
from pythonjsonlogger import jsonlogger

# 1. Define a custom formatter class
class SingaporeJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(SingaporeJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Override the 'timestamp' field with SGT time
        if self.timestamp:
            sgt_zone = timezone(timedelta(hours=8)) # Singapore is UTC+8
            now = datetime.now(sgt_zone)
            log_record['timestamp'] = now.isoformat()