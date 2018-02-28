
# Author: Bjoern Riemer
# GTPU handler library to work with corenet.py & libmich to use the kernel-mode gtpu implementation

import os
import subprocess
from libmich.mobnet.utils import log

import tun_conf as config

class GTPfake(object):

    DEBUG = ('ERR', 'WNG', 'INF', 'DBG')
    MOD = []

    INT_IP = '192.168.4.210'
    
    UE_SUBNET_PREFIX = None

    GTPif = "gtp1"
    #CMDgtp_tunnel = "gtp-tunnel"
    CMDgtp_tunnel = "/usr/local/bin/gtp_tunnel_mgmt.sh"

    ip2teid = dict()

    def __init__(self):
        self.start() # like AuC

    def start(self):
        self._log('INF', "GTPU kernel gtpu started, GTP interface: {0}".format(self.GTPif))

        # TODO: check if interface is available, if not create & configure
        gtp_link = subprocess.Popen(['gtp-link', 'add', self.GTPif], stderr = subprocess.PIPE)
        while True:
            if ('WARNING: attaching dummy socket descriptors. Keep '
			    'this process running for testing purposes.') in gtp_link.stderr.readline():
                break
        self._log('INF', 'gtp link added')
        subprocess.call(['ip', 'link', 'set', self.GTPif, 'mtu', '1500'])
        subprocess.call(['ip', 'route', 'add', self.UE_SUBNET_PREFIX + '.0/24', 'dev', self.GTPif])
        # Dummy IP goes back to host (tunneling)
        my_virt_ip = config.OWN_VIRT_IP
        ip_temp = my_virt_ip.split('.')
        ip_temp[2] = '100'
        own_ip = '.'.join(ip_temp)
        
        subprocess.call(['ip', 'route', 'add', own_ip, 'dev', 'eth0'])

    def stop(self):
        # TODO: delete interface
        pass

    def _log(self, logtype='DBG', msg=''):
        # logtype: 'ERR', 'WNG', 'INF', 'DBG'
        #print('[{0}] [GTPfake] {1}'.format(logtype, msg))
        if logtype in self.DEBUG:
            log('[{0}] [GTPfake] {1}'.format(logtype, msg))

    def add_mobile(self, mobile_IP='192.168.1.201', rnc_IP='10.1.1.1', TEID_from_rnc=0x1, TEID_to_rnc=0x1):
        # gtp-tunnel add <gtp device> <v1> <i_tei> <o_tei> <ms-addr> <sgsn-addr>
        #self._log(msg="add_mobile(%s,%s,%d,%d)" % (mobile_IP, rnc_IP,TEID_from_rnc, TEID_to_rnc))
        if self.ip2teid.has_key(mobile_IP):
            self.rem_mobile(mobile_IP)
        cmd = [self.CMDgtp_tunnel, 'add', self.GTPif, 'v1', str(TEID_from_rnc),
               str(TEID_to_rnc), mobile_IP, rnc_IP]
        #self._log('INF', "running cmd: " + str(cmd))
        subprocess.call(cmd)
        self.ip2teid[mobile_IP] = TEID_from_rnc
        self._log('INF', 'setting GTP tunnel for mobile with IP {0}'.format(
                  mobile_IP))

    def rem_mobile(self, mobile_IP='192.168.1.201'):
        #gtp-tunnel del <gtp device> <version> <tid>
        #self._log(msg="rem_mobile(%s)"%mobile_IP)
        teid = self.ip2teid.get(mobile_IP, None)
        if not teid is None:
            cmd = [self.CMDgtp_tunnel, 'del', self.GTPif, 'v1', str(teid)]
            #self._log('INF', "running cmd: " + str(cmd))
            subprocess.call(cmd)
            self.ip2teid.pop(mobile_IP)
            self._log('INF', 'unsetting GTP tunnel for mobile with IP '\
                      '{0}'.format(mobile_IP))
        else:
            self._log('WNG', "cant find TEID for ip %s" % mobile_IP)
