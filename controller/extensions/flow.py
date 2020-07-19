from pox.lib.packet import ipv4

class Flow:
    def __init__(self, src_ip, src_port, dst_ip, dst_port, protocol):
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.protocol = protocol

    def reverse(self):
        return Flow(self.dst_ip, self.dst_port, self.src_ip, self.src_port, self.protocol)

    @staticmethod
    def of(ip_pkt):
        inner_pkt = ip_pkt.payload    # TCP, UDP or ICMP packet
        src_port = inner_pkt.srcport if ip_pkt.protocol != ipv4.ICMP_PROTOCOL else 0   # Sets 0 to ports
        dst_port = inner_pkt.dstport if ip_pkt.protocol != ipv4.ICMP_PROTOCOL else 0   # (ofp_match default) since ICMP
        return Flow(ip_pkt.srcip, src_port, ip_pkt.dstip, dst_port, ip_pkt.protocol)   # doesn't have ports in header
