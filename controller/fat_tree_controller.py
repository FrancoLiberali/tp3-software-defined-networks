# coding=utf-8
from pox.core import core
import pox.openflow.discovery
import pox.host_tracker
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from extensions.shortest_paths_finder import ShortestPathsFinder
from extensions.switch import Switch
from extensions.link_to_switch import LinkToSwitch
from extensions.flow import Flow

log = core.getLogger()

class FatTreeController:

    def __init__(self):
        self.switches = {}  # {sw_dpid: Switch}
        self.hosts = {}     # {host_mac: LinkToSwitch}
        self.paths_finder = ShortestPathsFinder()
        core.call_when_ready(self.startup, ('openflow', 'openflow_discovery', 'host_tracker'))

    def startup(self):
        core.openflow.addListeners(self)
        core.openflow_discovery.addListeners(self)
        core.host_tracker.addListenerByName("HostEvent", self._handle_HostEvent)
        log.info('Controller initialized')

    def _handle_ConnectionUp(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#connectionup
        """
        dpid = dpid_to_str(event.dpid)
        log.info("Switch %s has come up.", dpid)
        if not dpid in self.switches:
            self.switches[dpid] = Switch(dpid, event.connection)
        log.info("Switches: %s.", self.switches)

    def _handle_ConnectionDown(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#connectiondown
        """
        dpid = dpid_to_str(event.dpid)
        assert dpid in self.switches

        log.info("Switch %s has come down.", dpid)
        self.switches.pop(dpid, None)
        for host, link_to_sw in self.hosts.items():
            if link_to_sw.sw_dpid == dpid:
                # the host is not connected to any switch so its not in the topology anymore
                self.hosts.pop(host)
                log.info("Hosts: %s.", self.hosts)
                self.paths_finder.notifyHostsChanged(self.hosts)
        self.paths_finder.notifyLinksChanged()
        log.info("Switches: %s.", self.switches)

    def _handle_HostEvent(self, event):
        """
        Listen to host_tracker events, fired up every time a host is up or down
        Fired up when a host make a ping to another.
        host_tracker fires a pingall to make this events fire
        Args:
            event: HostEvent listening to core.host_tracker
        """
        sw_dpid = dpid_to_str(event.entry.dpid)
        sw_port = event.entry.port

        assert sw_dpid in self.switches

        host_mac = event.entry.macaddr.toStr()
        if event.leave:
            log.info("Host %s has disconnected from %s:%s.", host_mac, sw_dpid, sw_port)
            # with default because it could be deleted if the host has no switch
            self.hosts.pop(host_mac, None)
        else:
            log.info("Host %s has connected to %s:%s.", host_mac, sw_dpid, sw_port)
            self.hosts[host_mac] = LinkToSwitch(self.switches[sw_dpid], sw_port)

        log.info("Hosts: %s.", self.hosts)
        self.paths_finder.notifyHostsChanged(self.hosts)

    def _handle_PacketIn(self, event):
        """Called when:
        - A packet does not have a matching FlowEntry in switch.
        - A packet matches with FlowEntry "send to controller action".
        Ref: https://noxrepo.github.io/pox-doc/html/#packetin
        Ref response:
            https://noxrepo.github.io/pox-doc/html/#ofp-flow-mod-flow-table-modification
            https://noxrepo.github.io/pox-doc/html/#match-structure
        """
        eth_packet = event.parsed
        if eth_packet.type == eth_packet.IP_TYPE:
            ip_packet = eth_packet.payload
            src_mac = eth_packet.src.toStr()
            dst_mac = eth_packet.dst.toStr()
            dpid = dpid_to_str(event.dpid)

            assert dpid in self.switches
            assert src_mac in self.hosts
            assert dst_mac in self.hosts

            new_flow = Flow.of(ip_packet)

            log.info("Packet arrived to switch %s:%s from %s<%s> to %s<%s>",
                     dpid, event.port, src_mac,
                     new_flow.src_ip, dst_mac, new_flow.dst_ip)

            # src and dest connected to the same sw
            if self.hosts[src_mac].sw_dpid == self.hosts[dst_mac].sw_dpid:
                sw = self.switches[dpid]
                self._set_shared_switch_output_port(sw, src_mac, dst_mac, new_flow)
            else:
                sw_linked_to_src = self.hosts[src_mac].sw
                sw_linked_to_dst = self.hosts[dst_mac].sw
                self._set_path(sw_linked_to_src, sw_linked_to_dst, src_mac, dst_mac, new_flow)

            # dont lose the packet that generated the packet in
            packet_out = of.ofp_packet_out(data=eth_packet, action=of.ofp_action_output(port=of.OFPP_TABLE))
            self.hosts[src_mac].sw.connection.send(packet_out)

    def _set_shared_switch_output_port(self, sw, src_mac, dst_mac, flow):
        sw.add_action_output(flow, self.hosts[dst_mac].port)            # Since hosts share same switch, the paths
        sw.add_action_output(flow.reverse(), self.hosts[src_mac].port)  # between them will be the same but reversed

    def _set_path(self, src_sw, dst_sw, src_mac, dst_mac, flow):
        path_to = self.paths_finder.get_path(src_sw.dpid, dst_sw.dpid)      # Since I'm already going from one switch to
        path_from = self.paths_finder.get_path(dst_sw.dpid, src_sw.dpid)    # another, I should define the way back as well
        paths = [path_to, path_from]                                        # in order to avoid another trip to controller
        macs = [dst_mac, src_mac]
        flows = [flow, flow.reverse()]

        for i in range(len(paths)):
            path, mac, flow = paths[i], macs[i], flows[i]

            for sw, output_port in path:
                if not output_port:     # the last switch
                    output_port = self.hosts[mac].port

                sw.add_action_output(flow, output_port)

    def _handle_LinkEvent(self, event):
        """
        Called when openflow_discovery discovers a new link
        """
        link = event.link
        dpid1 = dpid_to_str(link.dpid1)
        dpid2 = dpid_to_str(link.dpid2)

        assert dpid1 in self.switches
        assert dpid2 in self.switches

        sw_1 = self.switches[dpid1]
        sw_2 = self.switches[dpid2]
        sw_linked_by_1 = sw_1.get_switch_linked_on(link.port1)
        sw_linked_by_2 = sw_2.get_switch_linked_on(link.port2)
        # check if not setted yet because the link event is raised in both ways
        if (
            event.added
            and (sw_linked_by_1 != sw_2 or sw_linked_by_2 != sw_1)
        ):
            log.info("Link has been added from %s:%s to %s:%s", dpid1, link.port1, dpid2, link.port2)
            sw_1.add_link(link.port1, sw_2)
            sw_2.add_link(link.port2, sw_1)
            log.info("Switches: %s.", self.switches)
            self.paths_finder.notifyLinksChanged()
        # idem check if setted because the link event is raised in both ways
        elif (
            event.removed
            and (sw_linked_by_1 or sw_linked_by_2)
        ):
            log.info("Link has been removed from %s:%s to %s:%s", dpid1, link.port1, dpid2, link.port2)
            sw_1.remove_link(link.port1)
            sw_2.remove_link(link.port2)
            log.info("Switches: %s.", self.switches)
            self.paths_finder.notifyLinksChanged()

def launch():
    core.registerNew(FatTreeController)
    pox.openflow.discovery.launch()
    pox.host_tracker.launch()
