# coding=utf-8
from pox.core import core
import pox.openflow.discovery
from pox.lib.util import dpid_to_str

log = core.getLogger()

class FatTreeController:

    def __init__(self):
        core.call_when_ready(self.startup, ('openflow', 'openflow_discovery'))

    def startup(self):
        core.openflow.addListeners(self)
        core.openflow_discovery.addListeners(self)

    def _handle_ConnectionUp(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#connectionup
        """
        print('\nConnectionUp', event)

    def _handle_ConnectionDown(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#connectiondown
        """
        print('\nConnectionDown', event)

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

        print "\nPort %s on Switch %s has been %s." % (event.port, event.dpid, action)

    def _handle_FlowRemoved(self, event):
        """
        Ref: https://noxrepo.github.io/pox-doc/html/#flowremoved
        """
        print('\nFlowRemoved', event)

    def _handle_PacketIn(self, event):
        """Called when:
        - A packet does not have a matching FlowEntry in switch.
        - A packet matches with FlowEntry "send to controller action".
        Ref: https://noxrepo.github.io/pox-doc/html/#packetin
        """
        print('\nPacketIn', event)

    def _handle_LinkEvent(self, event):
        if event.added:
            action = "added"
        elif event.removed:
            action = "removed"
        else:
            action = "something else"

        print('\nLinkEvent action: {}'.format(action), event)


def launch():
    core.registerNew(FatTreeController)
    pox.openflow.discovery.launch()
