class LinkToSwitch:
  def __init__(self, sw, port):
    self.sw = sw
    self.port = port

  def __repr__(self):
    return str((str(self.sw), str(self.port)))

  @property
  def sw_dpid(self):
    return self.sw.dpid
