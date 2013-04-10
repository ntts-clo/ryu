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

import time
import json
import httplib
from argparse import ArgumentParser

from mn_ctl import MNCtl
from ryu.ofproto.ether import ETH_TYPE_ARP, ETH_TYPE_IP
from ryu.ofproto.inet import IPPROTO_TCP


parser = ArgumentParser(
    description='Topology auto creation '
                'and modification for test.')
parser.add_argument('--ryu_host', dest='ryu_host',
                    default='127.0.0.1', help='ryu ofp listen host')
parser.add_argument('--ryu_port', dest='ryu_port',
                    type=int, default=6633, help='ryu ofp listen port')
parser.add_argument('--rest_port', dest='rest_port',
                    type=int, default=8080, help='rest api listen port')
args = parser.parse_args()


_FLOW_PATH_BASE = '/stats/flowentry/%(cmd)s'
MN = MNCtl()


def main():
    MN.add_controller(args.ryu_host, args.ryu_port)

    ### Initializeing
    print """
Initializeing...
  addSwitch s1, s2, s3, s4, s5
  addLink   (s1, s2), (s2, s3)... (s5, s1)
"""
    # add switches
    for i in range(5):
        sw = 's%d' % (i + 1)
        MN.add_switch(sw)

    # add links
    for i in range(5):
        sw1 = 's%d' % (i + 1)
        sw2 = 's%d' % (i + 2)
        if sw1 == 's5':
            sw2 = 's1'
        MN.add_link(sw1, sw2)
    _wait(15)

    ### Added some switch
    print """
Added some switch
  addSwitch s6, s7, s8, s9, s10
"""
    for i in range(5, 10):
        sw = 's%d' % (i + 1)
        MN.add_switch(sw)
    _wait()

    ### Added some link
    print """
Added some link
  addLink   (s5, s6), (s6, s7) ...(s10, s1)
"""
    for i in range(4, 10):
        sw1 = 's%d' % (i + 1)
        sw2 = 's%d' % (i + 2)
        if sw1 == 's10':
            sw2 = 's1'
        MN.add_link(sw1, sw2)
    _wait()

    ### Added some link
    print """
Delete some links
  delLink  (s8, s9), (s9, s10), (s10, s1)
"""
    MN.del_link('s8', 's9')
    MN.del_link('s9', 's10')
    MN.del_link('s10', 's1')
    _wait()

    ### Delete some switch
    print """
Delete some switch
  delSwitch  s6, s7, s8, s9, s10
"""
    MN.del_switch('s6')
    MN.del_switch('s7')
    MN.del_switch('s8')
    MN.del_switch('s9')
    MN.del_switch('s10')
    _wait(10)

    ### Added some flow
    print """
Added some flow
    dpid   : 1
    rules  : dl_type=0x0800(ip), ip_proto=6(tcp), tp_src=100-104
    actions: OUTPUT: 2
"""
    path = _FLOW_PATH_BASE % {'cmd': 'add'}
    for tp_src in range(100, 105):
        body = {}
        body['dpid'] = 1
        body['match'] = {'dl_type': ETH_TYPE_IP,
                         'nw_proto': IPPROTO_TCP,
                         'tp_src': tp_src}
        body['actions'] = [{'type': "OUTPUT", "port": 2}]
        _do_request(path, 'POST', json.dumps(body))
    _wait(10)

    ### Modify some flow
    print """
Modify some flow
    dpid   : 1
    rules  : dl_type=0x0800(ip), ip_proto=6(tcp), tp_src=100-102
    actions: OUTPUT: 2->1
"""
    path = _FLOW_PATH_BASE % {'cmd': 'modify'}
    for tp_src in range(100, 103):
        body = {}
        body['dpid'] = 1
        body['match'] = {'dl_type': ETH_TYPE_IP,
                         'nw_proto': IPPROTO_TCP,
                         'tp_src': tp_src}
        body['actions'] = [{'type': "OUTPUT", "port": 1}]
        _do_request(path, 'POST', json.dumps(body))
    _wait(10)

    ### Delete some flow
    print """
Delete some flow
    dpid   : 1
    rules  : dl_type=0x0800(ip), ip_proto=6(tcp), tp_src=100-102
"""
    path = _FLOW_PATH_BASE % {'cmd': 'delete'}
    for tp_src in range(100, 103):
        body = {}
        body['dpid'] = 1
        body['match'] = {'dl_type': ETH_TYPE_IP,
                         'nw_proto': IPPROTO_TCP,
                         'tp_src': tp_src}
        _do_request(path, 'POST', json.dumps(body))
    _wait(10)

    ### Delete all flows
    print """
Delete all flows
    dpid   : 1
"""
    path = _FLOW_PATH_BASE % {'cmd': 'clear'}
    path += '/1'
    _do_request(path, 'DELETE')
    _wait()

    ### Delete all switches
    print "Delete all switches"
    MN.stop()
    print "Finished"


def _wait(wait=5):
    print "  ...waiting %s" % wait
    time.sleep(wait)


def _do_request(path, method="GET", body=None):
    address = '%s:%s' % (args.ryu_host, args.rest_port)
    conn = httplib.HTTPConnection(address)
    conn.request(method, path, body)
    res = conn.getresponse()
    if res.status in (httplib.OK,
                      httplib.CREATED,
                      httplib.ACCEPTED,
                      httplib.NO_CONTENT):
        return res

    raise httplib.HTTPException(
        res, 'code %d reason %s' % (res.status, res.reason),
        res.getheaders(), res.read())


if __name__ == "__main__":
    try:
        main()
    except:
        MN.stop()
        raise
