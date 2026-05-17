class _Radio:
    @property
    def connected(self):
        return True

    @property
    def ipv4_address(self):
        return "127.0.0.1"

    def connect(self, ssid, password):
        print("emulator wifi: pretend-connecting to {}".format(ssid))


radio = _Radio()
