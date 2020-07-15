class Path(list):
    """
    List of tuple (switch, port) to expresses witch port output take in each switch,
    in order to get a destiny
    the first switch is the origin and the last is the destiny.
    The port of the destiny whould be None because you allready are at destiny"""
    def add_jump(self, switch, port):
        self.append((switch, port))
    
    def add_destiny(self, switch):
        self.append((switch, None))

    def copy(self):
        return Path(self)
