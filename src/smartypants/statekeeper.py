from threading import Lock


class StateKeeper:
    def __init__(self):
        self.devices = {}
        self._lock = Lock()

    def add_device(self, device):
        with self._lock:
            self.devices[device.topic] = device

    def get_device_by_topic(self, topic: str):
        if topic in self.devices:
            return self.devices[topic]
        return None
