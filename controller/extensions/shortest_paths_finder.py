from pox.core import core
from path import Path

log = core.getLogger()

class ShortestPathsFinder:
    def __init__(self):
        self.sws_linked_to_a_host = []
        self.shortest_paths = {}    # origin_dpid: {destiny_dpid: Path}

    def notifyHostsChanged(self, hosts):
        old_sws_linked_to_a_host = self.sws_linked_to_a_host
        self._calculate_switches_linked_to_a_host(hosts)
        if old_sws_linked_to_a_host != self.sws_linked_to_a_host:
            log.info("Switches linked to a host: %s.",
                     self.sws_linked_to_a_host)
            self._calculate_shortest_paths()

    def notifyLinksChanged(self):
        self._calculate_shortest_paths()

    def get_path(self, origin, destiny):
        if origin in self.shortest_paths:
            if destiny in self.shortest_paths[origin]:
                # TODO use others paths when implementing load balancer
                return self.shortest_paths[origin][destiny][0]
        return None

    def _calculate_switches_linked_to_a_host(self, hosts):
        self.sws_linked_to_a_host = list(set(
            map(lambda link_to_sw: link_to_sw.sw, hosts.values())))

    def _calculate_shortest_paths(self):
        self.shortest_paths = {}

        for sw_origin in self.sws_linked_to_a_host:
            for sw_destiny in self.sws_linked_to_a_host:
                if (
                    sw_origin != sw_destiny
                    and not sw_destiny.dpid in self.shortest_paths.get(sw_origin.dpid, [])
                ):
                    shortest_paths = self._find_paths(sw_origin, sw_destiny, Path(), [])
                    self._set_paths(sw_origin, sw_destiny, shortest_paths)

        log.info("Shortest paths: %s.", self.shortest_paths)

    def _set_paths(self, sw_origin, sw_destiny, paths):
        shortest_paths_from_origin = self.shortest_paths.get(sw_origin.dpid, {})
        shortest_paths_from_origin[sw_destiny.dpid] = paths
        self.shortest_paths[sw_origin.dpid] = shortest_paths_from_origin

    def _find_paths(self, sw_origin, sw_destiny, actual_path, visited_sws):
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
                    for path in self._find_paths(sw, sw_destiny, new_actual_path, visited_sws):
                        paths_from_the_next_level.append(path)
        return self._keep_only_shortests(paths_from_the_next_level)

    def _keep_only_shortests(self, paths):
        if len(paths) > 0:
            shortest = len(paths[0])
            for path in paths:
                if len(path) < shortest:
                    shortest = len(path)
            return list(filter(lambda path: len(path) == shortest, paths))
        else:
            # no posible path between two switches
            return []
