# coding=utf-8
from pox.core import core
import pox.openflow.discovery
import pox.host_tracker
from pox.lib.util import dpid_to_str

log = core.getLogger()

SW_DPID_INDEX = 0
SW_PORT_INDEX = 1

class FatTreeController:

    def __init__(self):
        # keys sw_dpid, values {sw_port: sw_dpid_linked}
        self.switches = {}
        # keys host_mac, values (sw_dpid_linked, sw_port_linked}
        self.hosts = {}
        self.sws_linked_to_a_host = []
        self.shortests_paths = {}
        core.call_when_ready(
            self.startup, ('openflow', 'openflow_discovery', 'host_tracker'))

    def startup(self):
        core.openflow.addListeners(self)
        core.openflow_discovery.addListeners(self)
        core.host_tracker.addListenerByName("HostEvent", self._handle_HostEvent)
        log.info('Controller initialized')

    def calculate_shortests_paths(self):
        self.shortests_paths = {}

        for sw_origin in list(self.sws_linked_to_a_host):
            for sw_destiny in list(self.sws_linked_to_a_host):
                if (
                    sw_origin != sw_destiny
                    and not sw_destiny in self.shortests_paths.get(sw_origin, [])
                    and not sw_origin in self.shortests_paths.get(sw_destiny, [])
                ):
                    shortests_paths = self.find_paths(sw_origin, sw_destiny, [], [])
                    self.set_paths(sw_origin, sw_destiny, shortests_paths)
                    shortests_paths = list(map(lambda path: list(reversed(path)), shortests_paths))
                    self.set_paths(sw_destiny, sw_origin, shortests_paths)

        log.info("Shortest paths: %s.", self.shortests_paths)

    def set_paths(self, sw_origin, sw_destiny, paths):
        shortests_paths_from_origin = self.shortests_paths.get(sw_origin, {})
        shortests_paths_from_origin[sw_destiny] = paths
        self.shortests_paths[sw_origin] = shortests_paths_from_origin

    def find_paths(self, sw_origin, sw_destiny, actual_path, visited_sws):
        actual_path.append(sw_origin)
        paths_from_the_next_level = []
        visited_sws.append(sw_origin)

        linked_sws = self.switches[sw_origin].values()
        if sw_destiny in linked_sws:
            actual_path.append(sw_destiny)
            return [actual_path]
        else:
            old_visited_sws = visited_sws
            # update visited_sws to have the sws in the next level
            visited_sws = visited_sws + linked_sws
            for sw in linked_sws:
                # no go to a sw in a higher level
                if sw not in old_visited_sws:
                    # list(actual_path) to pass as copy
                    for path in self.find_paths(sw, sw_destiny, list(actual_path), visited_sws):
                        paths_from_the_next_level.append(path)
        return self.keep_only_shortests(paths_from_the_next_level)

    def keep_only_shortests(self, paths):
        if (len(paths) > 0):
            shortest = len(paths[0])
            for path in paths:
                if len(path) < shortest:
                    shortest = len(path)
            return list(filter(lambda path: len(path) == shortest, paths))
        else:
            # no posible path between two switches
            return []

    def calculate_switches_linked_to_a_host(self):
        self.sws_linked_to_a_host = set(
            map(lambda sw_dpid_and_port: sw_dpid_and_port[SW_DPID_INDEX], self.hosts.values()))

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
        self.hosts[host_mac] = (sw_dpid, sw_port)
        log.info("Switches: %s.", self.switches)
        log.info("Hosts: %s.", self.hosts)

        old_sws_linked_to_a_host = self.sws_linked_to_a_host
        self.calculate_switches_linked_to_a_host()
        if old_sws_linked_to_a_host != self.sws_linked_to_a_host:
            log.info("Switches linked to a host: %s.",
                     self.sws_linked_to_a_host)
            self.calculate_shortests_paths()

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
        self.calculate_shortests_paths()

def launch():
    core.registerNew(FatTreeController)
    pox.openflow.discovery.launch()
    pox.host_tracker.launch()
