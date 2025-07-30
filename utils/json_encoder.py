import json
from decimal import Decimal
from datetime import date, datetime, timedelta

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
