# coding=utf-8
from pox.core import core
import pox.openflow.discovery
import pox.host_tracker
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from extensions.shortest_paths_finder import ShortestPathsFinder, SW_DPID_INDEX, SW_PORT_INDEX

log = core.getLogger()

class FatTreeController:

    def __init__(self):
        # keys sw_dpid, values {sw_port: sw_dpid_linked}
        self.switches = {}
        # keys host_mac, values (sw_dpid_linked, sw_port_linked}
        self.hosts = {}
        self.paths_finder = ShortestPathsFinder()
        core.call_when_ready(
            self.startup, ('openflow', 'openflow_discovery', 'host_tracker'))

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
            self.switches[dpid] = {}
        log.info("Switches: %s.", self.switches)

    def _handle_ConnectionDown(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#connectiondown
        """
        dpid = dpid_to_str(event.dpid)
        assert dpid in self.switches

        log.info("Switch %s has come down.", dpid)
        self.switches.pop(dpid, None)
        for host, sw_dpid_and_port in self.hosts.items():
            if sw_dpid_and_port[SW_DPID_INDEX] == dpid:
                # the host is not connected to any switch so its not in the topology anymore
                self.hosts.pop(host)
                log.info("Hosts: %s.", self.hosts)
                self.paths_finder.notifyHostsChanged(self.switches, self.hosts)
        self.paths_finder.notifyLinksChanged(self.switches)
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
        host_mac = event.entry.macaddr.toStr()
        if event.leave:
            log.info("Host %s has disconnected from %s:%s.", host_mac,
                 sw_dpid, sw_port)
            # with default because it could be deleted if the host has no switch
            self.hosts.pop(host_mac, None)
        else:
            log.info("Host %s has connected to %s:%s.", host_mac,
                     sw_dpid, sw_port)
            self.hosts[host_mac] = (sw_dpid, sw_port)

        log.info("Hosts: %s.", self.hosts)
        self.paths_finder.notifyHostsChanged(self.switches,self.hosts)

    def _handle_PortStatus(self, event):
        """Called when:
        - A port status changes in a switch.
        Ref: https://noxrepo.github.io/pox-doc/html/#portstatus
        """
        if event.added:
            action = "added"
        elif event.deleted:
            action = "removed"
        else:
            action = "modified"

        # print "\nPort %s on Switch %s has been %s." % (event.port, event.dpid, action)

    def _handle_FlowRemoved(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#flowremoved
        """
        # print('\nFlowRemoved', event)

    def _handle_PacketIn(self, event):
        """Called when:
        - A packet does not have a matching FlowEntry in switch.
        - A packet matches with FlowEntry "send to controller action".
        Ref: https://noxrepo.github.io/pox-doc/html/#packetin
        Ref response: https://noxrepo.github.io/pox-doc/html/#ofp-flow-mod-flow-table-modification
        """
        eth_packet = event.parsed
        if eth_packet.type == eth_packet.IP_TYPE:
            ip_packet = eth_packet.payload
            src_mac = eth_packet.src.toStr()
            dst_mac = eth_packet.dst.toStr()
            log.info("Packet arrived to switch %s:%s from %s<%s> to %s<%s>",
                     dpid_to_str(event.dpid), event.port, src_mac,
                     ip_packet.srcip, dst_mac, ip_packet.dstip)

            assert src_mac in self.hosts
            assert dst_mac in self.hosts

            # src and dest connected to the same sw
            if self.hosts[src_mac][SW_DPID_INDEX] == self.hosts[dst_mac][SW_DPID_INDEX]:
                table_modification = of.ofp_flow_mod()
                table_modification.command = of.OFPFC_ADD # add a rule
                table_modification.match.dl_type = eth_packet.IP_TYPE
                table_modification.match.nw_src = ip_packet.srcip
                table_modification.match.nw_dst = ip_packet.dstip
                table_modification.actions.append(
                    of.ofp_action_output(port=self.hosts[dst_mac][SW_PORT_INDEX]))
                event.connection.send(table_modification)


    def _handle_LinkEvent(self, event):
        """
        Called when openflow_discovery discovers a new link
        """
        link = event.link
        dpid1 = dpid_to_str(link.dpid1)
        dpid2 = dpid_to_str(link.dpid2)

        assert dpid1 in self.switches
        assert dpid2 in self.switches

        # check if not setted yet because the link event is raised in both ways
        if (
            event.added
            and self.switches[dpid1].get(link.port1, None) != dpid2
            and self.switches[dpid2].get(link.port2, None) != dpid1
        ):
            log.info("Link has been added from %s:%s to %s:%s", dpid1, link.port1, dpid2, link.port2)
            self.switches[dpid1][link.port1] = dpid2
            self.switches[dpid2][link.port2] = dpid1
            log.info("Switches: %s.", self.switches)
            self.paths_finder.notifyLinksChanged(self.switches)
        # idem check if setted because the link event is raised in both ways
        elif (
            event.removed
            and link.port1 in self.switches[dpid1]
            and link.port2 in self.switches[dpid2]
        ):
            log.info("Link has been removed from %s:%s to %s:%s", dpid1, link.port1, dpid2, link.port2)
            self.switches[dpid1].pop(link.port1)
            self.switches[dpid2].pop(link.port2)
            log.info("Switches: %s.", self.switches)
            self.paths_finder.notifyLinksChanged(self.switches)

def launch():
    core.registerNew(FatTreeController)
    pox.openflow.discovery.launch()
    pox.host_tracker.launch()
