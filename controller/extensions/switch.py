class Switch:
  def __init__(self, dpid, connection):
    self.dpid = dpid
    self.connection = connection
    self.links = {} # port: linked_sw

  def __repr__(self):
    return self.dpid

  def __eq__(self, other):
    if isinstance(other, Switch):
        return self.dpid == other.dpid
    return False

  def add_link(self, port, switch):
    self.links[port] = switch

  def remove_link(self, port):
    return self.links.pop(port, None)

  def get_linked_switches(self):
    return self.links.values()

  def get_links(self):
    return self.links.items()

  def get_switch_linked_on(self, port):
    return self.links.get(port, None)

  def get_port_to(self, switch):
    for port, linked_sw in self.links.items():
      if linked_sw == switch:
        return port
    return None
