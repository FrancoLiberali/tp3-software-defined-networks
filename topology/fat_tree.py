from mininet.topo import Topo

REQUIRED_PARAMS = [
    {
        'name': 'levels',
        'validations': [
            (lambda p: str(p).lstrip('-').isdigit(), 'Levels param must be numeric'),
            (lambda p: int(p) > 0, 'Levels must be at least 1')
        ]
    }
]

def _validate_params(params):
    for req_param in REQUIRED_PARAMS:
        param_name = req_param['name']

        if param_name not in params:
            raise RuntimeError("Missing required param '{}'.".format(param_name))

        param_value = params[param_name]
        for is_valid, error_msg in req_param['validations']:
            if not is_valid(param_value):
                raise RuntimeError(error_msg)


class FatTreeTopo(Topo):
    
    def __init__(self, *args, **params):
        super(FatTreeTopo, self).__init__(args, params)
        _validate_params(params)
        self.levels = params['levels']
        self.hosts_on_root = 3
        self.hosts_per_leaf = 1
        self.root_lvl = []
        self.leaf_lvl = []
        self._build()
        self._assign_root_hosts()
        self._assign_leaf_hosts()

    def _root_level(self):
        return 0

    def _leaf_level(self):
        return self.levels - 1

    def _build(self):
        curr_lvl = self._leaf_level()
        prev_lvl_switches = None

        while curr_lvl >= self._root_level():
            curr_lvl_switches = self._build_lvl_switches(curr_lvl, prev_lvl_switches)
            self._trace_level(curr_lvl, curr_lvl_switches)
            prev_lvl_switches = curr_lvl_switches
            curr_lvl -= 1

    def _build_lvl_switches(self, lvl, prev_lvl_sw):
        sw_quantity = 2**lvl
        curr_sw = 2 ** lvl
        switches = []

        for _ in range(sw_quantity):
            sw_name = self._switch_name(lvl, curr_sw)
            switch = self.addSwitch(sw_name)
            self._link(switch, prev_lvl_sw)
            switches.append(switch)
            curr_sw += 1

        return switches

    def _link(self, switch, prev_lvl_switches):
        if prev_lvl_switches is None:
            return

        for sw in prev_lvl_switches:
            self.addLink(switch, sw)

    def _trace_level(self, lvl, lvl_switches):
        if lvl == self._root_level():
            self.root_lvl = lvl_switches

        elif lvl == self._leaf_level():
            self.leaf_lvl = lvl_switches

    def _assign_root_hosts(self):
        root = self.root_lvl[0]

        for _ in range(self.hosts_on_root):
            host = self.addHost(self._host_name())
            self.addLink(root, host)

    def _assign_leaf_hosts(self):
        for switch in self.leaf_lvl:
            for _ in range(self.hosts_per_leaf):
                host = self.addHost(self._host_name())
                self.addLink(host, switch)

    def _switch_name(self, lvl, sw_number):
        return 's{}_{}'.format(sw_number, lvl)

    def _host_name(self):
        return 'h{}'.format(len(self.hosts()) + 1)


topos = {'fat_tree': FatTreeTopo}
