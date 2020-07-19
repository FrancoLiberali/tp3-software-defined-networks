class LinkToSwitch:
    def __init__(self, switches, sw_dpid, port):
        self.switches = switches
        self.sw_dpid = sw_dpid
        self.port = port

    def __repr__(self):
        return str((self.sw_dpid, str(self.port)))

    @property
    def sw(self):
        return self.switches[self.sw_dpid]
