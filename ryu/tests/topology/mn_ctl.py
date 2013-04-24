# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from argparse import ArgumentParser
from SimpleXMLRPCServer import SimpleXMLRPCServer

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch


parser = ArgumentParser()
parser.add_argument('--listen-host', dest='host', default='127.0.0.1')
parser.add_argument('--listen-port', dest='port', type=int, default=18000)
args = parser.parse_args()


class MNCtl(object):
    def __init__(self):
        self.mn = Mininet()
        self._links = {}

    def add_controller(self, ip, port):
        for controller in self.mn.controllers:
            if controller.ip == ip and controller.port == port:
                return
        controller = self.mn.addController(
            controller=RemoteController, ip=ip, port=port)
        controller.start()

    def add_switch(self, name):
        s = self.mn.addSwitch(name, cls=OVSKernelSwitch)
        s.start(self.mn.controllers)

    def del_switch(self, name):
        s = self.mn.get(name)
        s.stop()

    def add_link(self, node1, node2):
        [n1, n2] = self.mn.get(node1, node2)
        link = self.mn.addLink(n1, n2)
        self._links[(node1, node2)] = link
        n1.attach(link.intf1)
        n2.attach(link.intf2)

    def del_link(self, node1, node2):
        [n1, n2] = self.mn.get(node1, node2)
        if self._links.get((node1, node2)):
            link = self._links.pop((node1, node2))
            n1.detach(link.intf1)
            n2.detach(link.intf2)
        else:
            link = self._links.pop((node2, node1))
            n2.detach(link.intf1)
            n1.detach(link.intf2)
        link.delete()

    def stop(self):
        self.mn.stop()


class MNCtlServer(MNCtl):
    def __init__(self):
        super(MNCtlServer, self).__init__()
        self.server = SimpleXMLRPCServer((args.host, args.port),
                                         allow_none=True)

        self._register_function(self.add_controller)
        self._register_function(self.add_switch)
        self._register_function(self.del_switch)
        self._register_function(self.add_link)
        self._register_function(self.del_link)
        self._register_function(self.stop)

        print "Running on %s:%d" % (args.host, args.port)
        self.server.serve_forever()

    def _register_function(self, fnc):
        self.server.register_function(fnc)
        print "register %s" % (fnc.__name__)


if __name__ == "__main__":
    MNCtlServer()
