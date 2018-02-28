#!/usr/bin/python
# -*- coding: UTF-8 -*-
#/**
# * Software Name : corenet
# * Version : 0.1.0
# *
# * Copyright © 2015. Benoit Michau. ANSSI.
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License version 2 as published
# * by the Free Software Foundation.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# * GNU General Public License for more details.
# *
# * You will find a copy of the terms and conditions of the GNU General Public
# * License version 2 in the "license.txt" file or
# * see http://www.gnu.org/licenses/ or write to the Free Software Foundation,
# * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
# *
# *--------------------------------------------------------
# * File Name : corenet.py
# * Created : 2015-09-05
# * Authors : Benoit Michau
# *--------------------------------------------------------
#*/

# Optimized for CNI by Caner Bektas (caner.bektas@tu-dortmund.de)
# Prepared for Docker Integration and further optimized for tinyLTE by
# Philipp Gorczak and Fabian Eckermann {philipp.gorczak, fabian.eckermann}@tu-dortmund.de

# For extracting interface information
import netifaces as ni

# IPython interactive shell
import re
import signal
import subprocess
import sys

import corenet_conf as config

# Import all Libs in following folder (for CryptoMobile)
sys.path.append("/usr/corenet/deps")

from time import sleep
from IPython.terminal.embed import InteractiveShellEmbed
#
from libmich.utils.repr import *
from libmich.formats.L3Mobile import parse_L3
from libmich.mobnet.MME import *
from libmich.mobnet.AuC import AuC
from libmich.mobnet.ARPmgr import ARPd
from libmich.mobnet.SMSmgr import SMSRelay
from libmich.mobnet.utils import mac_aton
from GTPfake import GTPfake as GTPUd

### Initial settings ###
#SGi (External Net) and S1 (eNodeB) Interface names
sgi_if = 'eth0'
s1_if = 'eth1'

# SCTP and GTP Port
sctp_port = 36412
gtp_port = 2152

# MAC- and IP-address of gateway to external network
#(SGi Interface is in LAN with SDN-Network, so define self as Gateway)
def get_gateway_mac(gateway_ip):
    """ HACK for getting the gateway MAC using its IP. """
    subprocess.check_output(['ping', '-c', '1', gateway_ip])
    arp = subprocess.check_output(['arp', '-n']).splitlines()
    gw_mac_re = re.compile(r'^.*ether\s+([0-9a-f:]{17})')
    for l in arp:
        if l.startswith(gateway_ip):
            return gw_mac_re.match(l).group(1)
    else:
        raise RuntimeError('Could not resolve gateway MAC.')

# IP given to UE on SGi (External)
ue_subnet_prefix = config.UE.itervalues().next()['IP'][:-4]
ue_ip_pool = []

def main():
    UE = config.UE

    gw_mac = get_gateway_mac(config.SGI_GW_IP)

    # Get IP and MAC address of the Intefaces
    ip = ni.ifaddresses(sgi_if)[2][0]['addr']
    mac = ni.ifaddresses(sgi_if)[17][0]['addr']
    sgi_ip = str(ip)
    sgi_mac = str(mac)

    ip = ni.ifaddresses(s1_if)[2][0]['addr']
    s1_ip = str(ip)

    # debugging / tracing level
    AuC.DEBUG = ('ERR', 'WNG', 'INF')
    AuC.AuC_db_path = config.AUC_DB_PATH
    ARPd.DEBUG = ('ERR', 'WNG', 'INF')
    GTPUd.DEBUG = ('ERR', 'WNG', 'INF')#, 'DBG')
    SMSRelay.DEBUG = ('ERR', 'WNG', 'INF')#, 'DBG')
    MMEd.DEBUG = ('ERR', 'WNG', 'INF')#, 'DBG')
    MMEd.TRACE_SK = False
    MMEd.TRACE_ASN1 = False
    MMEd.TRACE_SEC = False
    MMEd.TRACE_NAS = False
    MMEd.TRACE_SMS = False
    MMEd_server_addr = (s1_ip, sctp_port)

    ### ARPd config ###
    # ARP resolver for the PGW on SGi
    ARPd.GGSN_ETH_IF = sgi_if
    ARPd.GGSN_MAC_ADDR = sgi_mac
    ARPd.GGSN_IP_ADDR = sgi_ip
    # IP given to UE on SGi
    ARPd.SUBNET_PREFIX = ue_subnet_prefix
    ARPd.IP_POOL = ue_ip_pool
    for ue_config in UE.values():
        ARPd.IP_POOL.append(ue_config['IP'])
    # IPv4 1st hop after PGW on SGi
    ARPd.ROUTER_MAC_ADDR = gw_mac
    # ARPd.ROUTER_IP_ADDR = gw_ip

    ### GTPUd config ###
    # GTP user-plane packets forwarder
    # internal interface (SGW S1U user-plane)
    GTPUd.INT_IP = s1_ip
    GTPUd.INT_PORT = gtp_port
    GTPUd.UE_SUBNET_PREFIX = ue_subnet_prefix
    
    # GTP User-Plane handler external interface (PGW SGi)
    GTPUd.EXT_IF = ARPd.GGSN_ETH_IF # same as ARPd.GGSN_ETH_IF
    GTPUd.GGSN_MAC_ADDR = ARPd.GGSN_MAC_ADDR # same as ARPd.GGSN_MAC_ADDR
    # mobile traffic filtering
    GTPUd.BLACKHOLING = False # allow all the traffic from handsets
    #GTPUd.BLACKHOLING = 'ext' # allow only the traffic on the local LAN, and on allowed ports for external networks
    #GTPUd.BLACKHOLING = True # discard all the traffic from handsets, except on allowed ports
    GTPUd.WL_ACTIVE = True # enables whitelist ports when BLACKHOLING is enabled
    GTPUd.WL_PORTS = [('UDP', 53), ('UDP', 123)] # allow only those ports when BLACKHOLING is enabled

    ### SMS Relay config ###
    SMSRelay.SMSC_RP_NUM = '990123' # SMS Relay phone number
    SMSRelay.TIMEZONE = 0x80

    ### MME config ###
    MMEd.ConfigS1 = {
    'MMEname': config.MME_NAME, # optional
    'ServedGUMMEIs': [
        {'servedPLMNs': [bytes(PLMN(config.MCC + config.MNC))], #(PLMN = MCC + MNC - First 5 digits of IMSI)
         'servedGroupIDs': [unhexlify(config.MME_GROUP)],
         'servedMMECs': [unhexlify(config.MME_CODE)]}
        ], # mandatory, at least 1
    'RelativeMMECapacity': 100, # mandatory, 0 < X < 255
    'MMERelaySupportIndicator': None, # optional
    'CriticalDiagnostics': None, # optional, 'true' otherwise
    }
    # keeping track of all procedures t(for debugging purpose)
    ENBd.TRACE = True # trace all S1 eNB-related procedures
    UEd.TRACE_S1 = True # trace all S1 UE-related procedures
    UEd.TRACE_NAS = True # trace all NAS procedures
    UEd.TRACE_SMS = True # trace all SMS procedures
    # NAS security
    UEd.NASSEC_MAC = True # enforce NAS security
    # UEd.NASSEC_ULCNT = True # enforce NAS UL count
    UEd.AUTH_POL_ATT = 1 # attach authentication policy
    UEd.AUTH_POL_TAU = 1 # TAU authentication policy
    UEd.AUTH_POL_SERV = 10 # service request authentication policy
    UEd.SMC_IMEI_POL = 1 # request IMEISV only once during security mode ctrl
    #UEd.SMC_EEA = [0, 1, 2, 3] # encryption algorithm priority: 0:None, 1:SNOW, 2:AES, 3:ZUC
    #UEd.SMC_EIA = [1, 2, 3] # integrity protection algorithm priority: 0:None (emergency call only), 1:SNOW, 2:AES, 3:ZUC
    UEd.SMC_EEA = [0] # encryption algorithm priority: 0:None, 1:SNOW, 2:AES, 3:ZUC
    UEd.SMC_EIA = [1, 2] # integrity protection algorithm priority: 0:None (emergency call only), 1:SNOW, 2:AES, 3:ZUC
    # ATTACH extended features
    UEd.ATT_EQU_PLMN = None # equivalent PLMNs
    UEd.ATT_ECN_LIST = None # list of (emergency service category, emergency number)
    UEd.ATT_EPS_FEAT = None # EPS network feature support
    UEd.ATT_ADD_UPD = None
    # APN
    UEd.ESM_APN_DEF = config.DEF_APN # default APN
    UEd.ESM_PDN = config.PDN

    # start AuC, ARPd and GTPUd, MMEd
    log('\n\n\n', withdate=False)
    log('--------########<<<<<<<<////////:::::::: CORENET ::::::::\\\\\\\\\\\\\\\\>>>>>>>>########--------')
    log('...')
    AUCd = AuC()
    UEd.AUTH_AMF = AUCd.AMF # Authentication Management Field
    # and finally start ARP resolver
    ARP = ARPd()
    GTPUd.ARPd = ARP
    GTPd = GTPUd() # this starts ARPd automatically !!! not if gtpfake
    SMSd = SMSRelay()
    MME = MMEd(config={'server': MMEd_server_addr,
                       'ue': UE,
                       'enb': {},
                       })

    # You can add the TCPSYNACK module in GTPd.MOD to auto-answer to UE TCP-SYN packets
    # and / or DNSRESP module in GTPd.MOD to auto-answer to UE DNS requests
    # (do not forget to enable GTPd.BLACKHOLING in this case)
    #MOD.GTPUd = GTPd
    #GTPd.MOD = [DNSRESP, TCPSYNACK]
    GTPd.MOD = []

    # configure MMEd IO to AuC, GTPUd and SMSRelay
    MME.AUCd = AUCd
    MME.GTPd = GTPd
    MME.SMSd = SMSd
    SMSd.MME = MME

    def stop():
        AUCd.stop()
        ARPd.stop()
        GTPd.stop()
        SMSd.stop()
        MME.stop()

    # configure IPython corenet banner
    _ipy_banner = \
        'EPC 0.2.0 loaded -- interactive Evolved Packet Core\n' \
        'ASN.1 classes: ASN1Obj, PER, GLOBAL\n' \
        'Protocol stack classes: ENBd, UEd\n' \
        'instances:\n' \
        '\tMME: MME server, handling .UE and .ENB\n' \
        '\tAUCd: AuC Authentication center\n' \
        '\tGTPd: GTPU tunnel manager\n' \
        '\tSMSd: SMS relay\n' \
        'functions:\n' \
        '\tstop: stops all 3 running instances\n' \
        '\tshow: nicely prints signalling packets\n' \
        '\tparse_L3: parses NAS-PDU\n' \
        'MME-initiated procedures:\n' \
        '\tIdentification, GUTIReallocation, Authentication, ' \
        'SecurityModeControl, EMMInformation, MMEDetach'

    # configure IPython kernel namespace
    _ipy_ns = {}
    _ipy_ns['GLOBAL'] = GLOBAL
    _ipy_ns['ASN1Obj'] = ASN1Obj
    _ipy_ns['PER'] = PER
    _ipy_ns['UEd'] = UEd
    _ipy_ns['ENBd'] = ENBd
    _ipy_ns['MME'] = MME
    _ipy_ns['AUCd'] = AUCd
    _ipy_ns['GTPd'] = GTPd
    _ipy_ns['SMSd'] = SMSd
    _ipy_ns['show'] = show
    _ipy_ns['stop'] = stop
    _ipy_ns['parse_L3'] = parse_L3
    _ipy_ns['Identification'] = Identification
    _ipy_ns['GUTIReallocation'] = GUTIReallocation
    _ipy_ns['Authentication'] = Authentication
    _ipy_ns['SecurityModeControl'] = SecurityModeControl
    _ipy_ns['EMMInformation'] = EMMInformation
    _ipy_ns['MMEDetach'] = MMEDetach

    # TODO use click
    if len(sys.argv) >= 2 and sys.argv[1] == '--interactive':
        # interactive epc session
        ipshell = InteractiveShellEmbed(user_ns=_ipy_ns, \
                                        banner1=_ipy_banner, \
                                        exit_msg='leaving corenet now...')
        ipshell()
    else:
        try:
            signal.pause()
        except KeyboardInterrupt:
            pass
    #
    # before exiting, we need to close everything properly
    # MMEd, GTPUd, AuC, SMSRelay ...
    stop()
    #
    # exit the application
    sys.exit()

if __name__ == '__main__':
    main()
