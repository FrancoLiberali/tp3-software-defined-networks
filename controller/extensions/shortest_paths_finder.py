from pox.core import core
from .path import Path

log = core.getLogger()

SW_DPID_INDEX = 0
SW_PORT_INDEX = 1

class ShortestPathsFinder:
    def __init__(self):
        self.sws_linked_to_a_host = []
        # origin_dpid: {destiny_dpid: Path}
        self.shortest_paths = {}

    def notifyHostsChanged(self, switches, hosts):
        old_sws_linked_to_a_host = self.sws_linked_to_a_host
        self._calculate_switches_linked_to_a_host(hosts)
        if old_sws_linked_to_a_host != self.sws_linked_to_a_host:
            log.info("Switches linked to a host: %s.",
                     self.sws_linked_to_a_host)
            self._calculate_shortest_paths(switches)

    def notifyLinksChanged(self, switches):
        self._calculate_shortest_paths(switches)

    def _calculate_switches_linked_to_a_host(self, hosts):
        self.sws_linked_to_a_host = set(
            map(lambda sw_dpid_and_port: sw_dpid_and_port[SW_DPID_INDEX], hosts.values()))

    def _calculate_shortest_paths(self, switches):
        self.shortest_paths = {}

        for sw_origin in list(self.sws_linked_to_a_host):
            for sw_destiny in list(self.sws_linked_to_a_host):
                if (
                    sw_origin != sw_destiny
                    and not sw_destiny in self.shortest_paths.get(sw_origin, [])
                ):
                    shortest_paths = self._find_paths(switches, switches[sw_origin], switches[sw_destiny], Path(), [])
                    self._set_paths(sw_origin, sw_destiny, shortest_paths)

        log.info("Shortest paths: %s.", self.shortest_paths)

    def _set_paths(self, sw_origin, sw_destiny, paths):
        shortest_paths_from_origin = self.shortest_paths.get(sw_origin, {})
        shortest_paths_from_origin[sw_destiny] = paths
        self.shortest_paths[sw_origin] = shortest_paths_from_origin

    def _find_paths(self, switches, sw_origin, sw_destiny, actual_path, visited_sws):
        visited_sws.append(sw_origin)

        port_to_destiny = sw_origin.get_port_to(sw_destiny)
        if port_to_destiny:
            actual_path.add_jump(sw_origin, port_to_destiny)
            actual_path.add_destiny(sw_destiny)
            return [actual_path] # returns a list of posible paths
        else:
            paths_from_the_next_level = []
            linked_sws = sw_origin.get_linked_switches()

            old_visited_sws = visited_sws
            # update visited_sws to have the sws in the next level
            visited_sws = visited_sws + linked_sws
            for port, sw in sw_origin.get_links():
                # no go to a sw in a higher level
                if sw not in old_visited_sws:
                    new_actual_path = actual_path.copy()
                    new_actual_path.add_jump(sw_origin, port)
                    for path in self._find_paths(switches, sw, sw_destiny, new_actual_path, visited_sws):
                        paths_from_the_next_level.append(path)
        return self._keep_only_shortests(paths_from_the_next_level)

    def _keep_only_shortests(self, paths):
        if (len(paths) > 0):
            shortest = len(paths[0])
            for path in paths:
                if len(path) < shortest:
                    shortest = len(path)
            return list(filter(lambda path: len(path) == shortest, paths))
        else:
            # no posible path between two switches
            return []
