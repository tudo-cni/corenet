
# Author: Bjoern Riemer
# GTPU handler library to work with corenet.py & libmich to use the kernel-mode gtpu implementation

import os
from libmich.mobnet.utils import log

class GTPfake(object):

    DEBUG = ('ERR', 'WNG', 'INF', 'DBG')
    MOD = []

    INT_IP = '192.168.4.210'

    GTPif = "gtp1"
    CMDprefix = "ip netns exec gtpu " # run commands in network namespace 'gtpu'

    ip2teid = dict()

    def start(self):
        _log('INF', "GTPU kernel gtpu started")
        _log('INF', "GTP interface: %s" % self.GTPif)
        _log('INF', "CMD prefix: %s" % self.CMDprefix)
        # TODO: check if interface is available, if not create & configure
        #   gtp-link add gtp1
        #   ip link set gtp1 mtu 1500
        #   ip r a 192.168.3.0/24 dev gtp1

    def stop(self):
        # TODO: delete interface
        pass

    def _log(self, logtype='DBG', msg=''):
        # logtype: 'ERR', 'WNG', 'INF', 'DBG'
        if logtype in self.DEBUG:
            print('[{0}] [GTPfake] {1}'.format(logtype, msg))
            log('[{0}] [GTPfake] {1}'.format(logtype, msg))

    def add_mobile(self, mobile_IP='192.168.3.100', rnc_IP='192.168.4.90', TEID_from_rnc=0x1, TEID_to_rnc=0x1):
        # gtp-tunnel add <gtp device> <v1> <i_tei> <o_tei> <ms-addr> <sgsn-addr>
        self._log("add_mobile(%s,%s,%d,%d)" % (mobile_IP, rnc_IP,TEID_from_rnc, TEID_to_rnc))
        if self.ip2teid.has_key(mobile_IP):
            self.rem_mobile(mobile_IP)
        cmd = "%s gtp-tunnel add %s v1 %d %d %s %s" % (self.CMDprefix, self.GTPif, TEID_from_rnc, TEID_to_rnc, mobile_IP, rnc_IP)
        self._log("running cmd: %s"%cmd)
        os.system(cmd)
        self.ip2teid[mobile_IP] = TEID_from_rnc

    def rem_mobile(self, mobile_IP='192.168.3.100'):
        #gtp-tunnel del <gtp device> <version> <tid>
        self._log("rem_mobile(%s)"%mobile_IP)
        teid = self.ip2teid.get(mobile_IP, None)
        if not teid is None:
            cmd = "%s gtp-tunnel del %s v1 %d" % (self.CMDprefix, self.GTPif, teid)
            self._log("running cmd: %s"%cmd)
            os.system(cmd)
            self.ip2teid.pop(mobile_IP)
        else:
            self._log('WNG', "cant find TEID for ip %s" % mobile_IP)
