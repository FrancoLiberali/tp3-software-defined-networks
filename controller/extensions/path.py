class Path(list):
    """
    List of tuple (switch, port) to express which port output take in each switch,
    in order to get a destiny
    the first switch is the origin and the last is the destiny.
    The port destiny's should be None because you are at destiny already"""
    def add_jump(self, switch, port):
        self.append((switch, port))
    
    def add_destiny(self, switch):
        self.append((switch, None))

    def copy(self):
        return Path(self)
