"""Real loopback TCP: RX must survive TX completion + the old five-second join."""
import hashlib
import socket
import threading
import time
import unittest
import m0_winxdp_pressure_tcp as tcp

class DrainTest(unittest.TestCase):
    def test_peer_tail_after_old_join(self):
        old=tcp.DRAIN_SECONDS
        tcp.DRAIN_SECONDS=12
        payload=b"late real TCP bytes"*4096
        errors=[]
        try:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1",0))
                listener.listen(1)
                with socket.create_connection(listener.getsockname(),timeout=3) as client:
                    peer,_=listener.accept()
                    def remote():
                        try:
                            with peer:
                                peer.settimeout(3)
                                while peer.recv(65536):pass
                                time.sleep(6)
                                peer.sendall(payload)
                                peer.shutdown(socket.SHUT_WR)
                        except Exception as exc:errors.append(repr(exc))
                    worker=threading.Thread(target=remote)
                    worker.start()
                    try:row=tcp.exchange(client,.2,1,True,True,True)
                    finally:worker.join(15)
                    self.assertFalse(worker.is_alive())
                    self.assertEqual(errors,[])
                    self.assertEqual(row["errors"],[])
                    self.assertEqual(row["rx_end"],"eof")
                    self.assertEqual(row["received"],len(payload))
                    self.assertEqual(row["rx_sha256"],hashlib.sha256(payload).hexdigest())
                    self.assertEqual(row["rx_after_business_bytes"],len(payload))
                    self.assertGreater(row["rx_eof_elapsed_s"],6)
        finally:tcp.DRAIN_SECONDS=old

if __name__=="__main__":unittest.main()
