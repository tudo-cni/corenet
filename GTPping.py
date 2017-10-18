
# Author: Bjoern Riemer
# simple program to answer GTP Ping messages used in GTPU 

import os
import signal
from struct import pack, unpack
from threading import Thread
from socket import socket, timeout, error, \
    ntohs, htons, inet_aton, inet_ntoa, \
    AF_PACKET, SOCK_RAW, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
#from libmich.mobnet.utils import log

def threadit(f, *args, **kwargs):
    th = Thread(target=f, args=args, kwargs=kwargs)
    th.start()
    return th

class GTPping(object):
    '''
    GTPU ping handler
    '''
    #
    # verbosity level: list of log types to display when calling
    # self._log(logtype, msg)
    DEBUG = ('ERR', 'WNG', 'INF', 'DBG')
    #
    # packet buffer space (over MTU...)
    BUFLEN = 2048

    INT_IP = '0.0.0.0'
    INT_PORT = 2152

    def __init__(self):
        #
        # create an UDP socket on the RNC / eNobeB side, on port 2152
        self.int_sk = socket(AF_INET, SOCK_DGRAM)
        # configure timeout, binding and rebinding on same address
        #self.int_sk.settimeout(0.003)
        #self.int_sk.setblocking(0)
        self.int_sk.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.int_sk.bind((self.INT_IP, self.INT_PORT))
        #
        # interrupt handler
        def sigint_handler(signum, frame):
            self._log('INF', 'CTRL+C caught')
            self.stop()
        #signal.signal(signal.SIGINT, sigint_handler)
        #
        # and start listening and transferring packets in background
        self._listening = True
        self._listener_t = threadit(self.listen)
        self._log('INF', 'GTPU handler started')


    def _log(self, logtype='DBG', msg=''):
        # logtype: 'ERR', 'WNG', 'INF', 'DBG'
        if logtype in self.DEBUG:
            #log('[{0}] [GTPUd] {1}'.format(logtype, msg))
            print('[{0}] [GTPUd] {1}'.format(logtype, msg))

    def listen(self):
        while self._listening:
            try:
                (bufint, from_address) = self.int_sk.recvfrom(self.BUFLEN)
            except timeout:
                # nothing to read anymore
                self._log('INF', 'read timeout')
                pass
            except error as err:
                self._log('ERR', 'internal network IF error '\
                          '(recv): {0}'\
                          .format(err))
                self.stop()
            else:
                self.handle_gtp_ping(bufint,from_address)

    def stop(self):
        # stop local GTPU handler
        if self._listening:
            self._listening = False
            sleep(self.SELECT_TO * 2)
            try:
                # closing sockets
                self.int_sk.close()
            except Exception as err:
                self._log('ERR', 'socket error: {0}'.format(err))

    def handle_gtp_ping(self, buf='\0', from_address=None):
        # extract the GTP header
        try:
            flags, msgtype, msglen, teid, seq = unpack('>BBHIH', buf[:10])
        except:
            self._log('WNG', 'invalid GTP packet')
            return
        if msgtype == 0x01:
            self._log('INF', "got GTP ping seq=%d teid=%d" % (seq,teid))
            if flags & 0x02:
                pass
            try:
                gtphdr = pack('>BBHIH', flags, 0x02, msglen, teid, seq)
                ret = self.int_sk.sendto(gtphdr+buf[10:], from_address)
            except Exception as err:
                self._log('ERR', 'internal network IF error (sendto): {0}'.format(err))
        else:
            #self._log('DBG', "packet is not GTP ping")
            pass

if __name__ == '__main__':
    gtpping = GTPping()
