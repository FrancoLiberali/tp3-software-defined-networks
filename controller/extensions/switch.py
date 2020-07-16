from pox.openflow.flow_table import FlowTable, TableEntry
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet

class Switch:
  def __init__(self, dpid, connection):
    self.dpid = dpid
    self.connection = connection
    self.links = {} # port: linked_sw
    self.flow_table = FlowTable()

  def __repr__(self):
    return self.dpid

  def __eq__(self, other):
    if isinstance(other, Switch):
        return self.dpid == other.dpid
    return False

  def __hash__(self):
    return hash(self.dpid)

  def add_link(self, port, switch):
    self.links[port] = switch

  def remove_link(self, port):
    self.flow_table.remove_matching_entries(
      of.ofp_match(dl_type=ethernet.IP_TYPE),
      out_port=port
    )
    self.connection.send(
      of.ofp_flow_mod(
          command=of.OFPFC_DELETE,
          action=of.ofp_action_output(port=port),
          match=of.ofp_match(dl_type=ethernet.IP_TYPE)
      )
    )
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

  def add_action_output(self, src_ip, dst_ip, output_port):
    new_entry = TableEntry(
        match=of.ofp_match(
            # TODO add dst_port, src_port and protocol of match to complete flow info
            dl_type=ethernet.IP_TYPE,
            nw_src=src_ip,
            nw_dst=dst_ip
        ),
        actions=[
            of.ofp_action_output(port=output_port)
        ]
    )
    overlapping_entry = self._find_overlapping_entry(new_entry)
    command = of.OFPFC_ADD
    if overlapping_entry:
      self.flow_table.remove_entry(overlapping_entry)
      command = of.OFPFC_MODIFY

    self.flow_table.add_entry(new_entry)
    flow_mod = new_entry.to_flow_mod()
    flow_mod.command = command
    self.connection.send(flow_mod)

  def _find_overlapping_entry(self, entry):
    for e in self.flow_table.entries:
      if e.is_matched_by(entry.match) or entry.is_matched_by(e.match):
        return e
    return None
