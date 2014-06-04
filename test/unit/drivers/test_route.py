# Copyright 2014 DreamHost, LLC
#
# Author: DreamHost, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import mock
import unittest2

from akanda.router import models
from akanda.router.drivers import route


class RouteTest(unittest2.TestCase):

    def setUp(self):
        self.mgr = route.RouteManager()

    def test_get_default_gateway_v6_missing(self):
        output = 'route: writing to routing socket: No such process\n'
        with mock.patch.object(self.mgr, 'sudo') as sudo:
            sudo.return_value = output
            self.assertEqual(
                None,
                self.mgr._get_default_gateway('-inet6')
            )
            sudo.assert_called_with('-n', 'get', '-inet6', 'default')

    def test_get_default_gateway_v6(self):
        output = """
   route to: ::
destination: ::
       mask: default
    gateway: fdee:9f85:83be::1
  interface: vio1
 if address: fdee:9f85:83be:0:f816:3eff:fe7b:6263
   priority: 8 (static)
      flags: <UP,GATEWAY,DONE,STATIC>
     use       mtu    expire
       0         0         0
"""
        with mock.patch.object(self.mgr, 'sudo') as sudo:
            sudo.return_value = output
            self.assertEqual(
                'fdee:9f85:83be::1',
                self.mgr._get_default_gateway('-inet6')
            )
            sudo.assert_called_with('-n', 'get', '-inet6', 'default')

    def test_get_default_gateway_v4(self):
        output = """
   route to: default
destination: default
       mask: default
    gateway: 192.168.122.1
  interface: vio0
 if address: 192.168.122.240
   priority: 8 (static)
      flags: <UP,GATEWAY,DONE,STATIC>
      label: DHCLIENT 20978
     use       mtu    expire
   73687         0         0
sockaddrs: <DST,GATEWAY,NETMASK,IFP,IFA,LABEL>
"""
        with mock.patch.object(self.mgr, 'sudo') as sudo:
            sudo.return_value = output
            self.assertEqual(
                '192.168.122.1',
                self.mgr._get_default_gateway('-inet')
            )
            sudo.assert_called_with('-n', 'get', '-inet', 'default')

    def test_set_default_v4_matches_current(self):
        ip_s = '192.168.122.1'
        ip = mock.MagicMock()
        ip.version = 4
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = ip_s
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                sudo.side_effect = AssertionError('should not be called')
                self.mgr._set_default_gateway(ip)

    def test_set_default_v4_changes_current(self):
        ip_s = '192.168.122.1'
        ip = mock.MagicMock()
        ip.version = 4
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = '192.168.122.254'
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                self.mgr._set_default_gateway(ip)
                sudo.assert_called_with('change', '-inet', 'default', ip_s)

    def test_set_default_v4_no_current(self):
        ip_s = '192.168.122.1'
        ip = mock.MagicMock()
        ip.version = 4
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = None
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                self.mgr._set_default_gateway(ip)
                sudo.assert_called_with('add', '-inet', 'default', ip_s)

    def test_set_default_v6_matches_current(self):
        ip_s = 'fe80::5054:ff:fee2:1d4f'
        ip = mock.MagicMock()
        ip.version = 6
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = ip_s
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                sudo.side_effect = AssertionError('should not be called')
                self.mgr._set_default_gateway(ip)

    def test_set_default_v6_changes_current(self):
        ip_s = 'fe80::5054:ff:fee2:1d4f'
        ip = mock.MagicMock()
        ip.version = 6
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = 'fe80::5054:ff:fee2:aaaa'
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                self.mgr._set_default_gateway(ip)
                sudo.assert_called_with('change', '-inet6', 'default', ip_s)

    def test_set_default_v6_no_current(self):
        ip_s = 'fe80::5054:ff:fee2:1d4f'
        ip = mock.MagicMock()
        ip.version = 6
        ip.__str__.return_value = ip_s
        with mock.patch.object(self.mgr, '_get_default_gateway') as get:
            get.return_value = None
            with mock.patch.object(self.mgr, 'sudo') as sudo:
                self.mgr._set_default_gateway(ip)
                sudo.assert_called_with('add', '-inet6', 'default', ip_s)

    def test_update_default_no_inputs(self):
        c = models.Configuration({})
        with mock.patch.object(self.mgr, '_set_default_gateway') as set:
            set.side_effect = AssertionError(
                'should not try to set default gw'
            )
            self.mgr.update_default(c)

    def test_update_default_v4_only(self):
        c = models.Configuration({'default_v4_gateway': '172.16.77.1'})
        with mock.patch.object(self.mgr, '_set_default_gateway') as set:
            self.mgr.update_default(c)
            set.assert_called_once_with(c.default_v4_gateway)

    def test_update_default_v6_only(self):
        subnet = dict(
            cidr='fe80::1/64',
            gateway_ip='fe80::1',
            dhcp_enabled=True,
            dns_nameservers=[],
        )
        network = dict(
            network_id='netid',
            name='thenet',
            interface=dict(ifname='ge0', addresses=['fe80::2']),
            allocations=[],
            subnets=[subnet],
            network_type='external',
        )
        c = models.Configuration({'networks': [network]})
        with mock.patch.object(self.mgr, '_set_default_gateway') as set:
            self.mgr.update_default(c)
            net = c.networks[0]
            snet = net.subnets[0]
            set.assert_called_once_with(snet.gateway_ip)
