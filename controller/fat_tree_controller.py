# coding=utf-8
from pox.core import core
import pox.openflow.discovery
import pox.host_tracker
from pox.lib.util import dpid_to_str

log = core.getLogger()

class FatTreeController:

    def __init__(self):
        # keys sw_dpid, values {sw_port: sw_dpid_linked or host_mac_linked}
        self.switches = {}
        # keys host_mac, values (sw_dpid_linked, sw_port_linked}
        self.hosts = {}
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
        # log.info("Switch %s has come down.", dpid_to_str(event.dpid))

    def _handle_HostEvent(self, event):
        """
        Listen to host_tracker events, fired up every time a host is up or down
        Fired up when a host make a ping to another.
        host_tracker fires a pingall to make this events fire
        Args:
            event: HostEvent listening to core.host_tracker
        """
        # la mac del host y al sw y puerto al que esta conectado
        sw_dpid = dpid_to_str(event.entry.dpid)
        sw_port = event.entry.port
        host_mac = event.entry.macaddr.toStr()
        log.info("Host %s is connected to %s:%s.", host_mac,
                 sw_dpid, sw_port)
        self.switches[sw_dpid][sw_port] = host_mac
        self.hosts[host_mac] = (sw_dpid, sw_port)
        log.info("Switches: %s.", self.switches)
        log.info("Hosts: %s.", self.hosts)

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
        """
        packet = event.parsed
        # log.info("Packet arrived to switch %s:%s from %s to %s",
                #  dpid_to_str(event.dpid), event.port, packet.src, packet.dst)

    def _handle_LinkEvent(self, event):
        """
        Called when openflow_discovery discovers a new link
        """
        if event.added:
            action = "added"
        elif event.removed:
            action = "removed"
        else:
            action = "something else"

        link = event.link
        log.info("Link has been %s from %s:%s to %s:%s", action, dpid_to_str(
            link.dpid1), link.port1, dpid_to_str(link.dpid2), link.port2)
        dpid1 = dpid_to_str(link.dpid1)
        dpid2 = dpid_to_str(link.dpid2)
        self.switches[dpid1][link.port1] = dpid2
        self.switches[dpid2][link.port2] = dpid1
        log.info("Switches: %s.", self.switches)

def launch():
    core.registerNew(FatTreeController)
    pox.openflow.discovery.launch()
    pox.host_tracker.launch()
