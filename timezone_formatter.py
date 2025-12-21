from datetime import datetime, timezone, timedelta
from pythonjsonlogger import jsonlogger


class SingaporeJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(SingaporeJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        if self.timestamp:
            sgt_zone = timezone(timedelta(hours=8))
            now = datetime.now(sgt_zone)
            log_record['timestamp'] = now.isoformat()