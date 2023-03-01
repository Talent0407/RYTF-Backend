import json
import time

import requests
from django.conf import settings
from sentry_sdk import capture_exception


class LoggingServiceError(Exception):
    pass


class LoggingService:
    def __init__(self):
        self.url = "https://api.graphjson.com/api/log"
        self.api_key = settings.GRAPH_JSON_API_KEY

    def log(self, event: dict):
        pass
        # no longer active to save bandwidth
        # if not settings.DEBUG:
        #     self._send_event(event)

    def _send_event(self, event):
        try:
            payload = {
                "api_key": self.api_key,
                "collection": "ryft",
                "timestamp": int(time.time()),
                "json": json.dumps(event),
            }
            r = requests.post(self.url, json=payload)
            return r.json()
        except LoggingServiceError as e:
            capture_exception(e)


logging_service = LoggingService()
