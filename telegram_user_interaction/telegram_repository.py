class TeleRepo:
    def __init__(self):
        self._repo = dict()

    def put(self, key, value):
        self._repo[key] = value

    def get(self, key):
        if key in self._repo:
            return self._repo[key]
        else:
            return None

    def delete(self, key):
        if key in self._repo:
            del self._repo[key]


message_repo = TeleRepo()
