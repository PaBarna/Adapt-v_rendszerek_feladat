#encoding: utf-8

import struct
import sys
import socket
import selectors
import time
import types
import json
from queue import Queue
from threading import Thread


class SocketClient:
    def __init__(self, ip, port, callback):
        """
        :param ip: Szerver IP
        :param port: Szerver PORT
        :param callback: Függvény referencia, melynek szignatúrája callback(fulljson, sendData), ahol a fulljson a szervertől érkező üzenet, a sendData a kliens küldő függvénye.
        Ez a callback meghívódik a klienshez érkező érvényes üzenetek esetén külön szálon futva.
        """
        self.host = ip
        self.port = port
        self.running = True
        self.t = None
        self.sendQueue = Queue()
        self.callback = callback

    def sendData(self, data):
        """
        :param data: Stringbe kódolt JSON, melyet ki kell küldeni a szervernek.
        :return:
        """
        self.sendQueue.put(data)


    def start(self):
        """
        A klienst külön szálon elindító metódus, nem blockol.
        :return:
        """
        self.running = True
        self.t = Thread(target=self._run)
        self.t.start()

    def stop(self):
        """
        A metódus megszakítja a kliens futását, és megvárja a feldolgozó szál leállását.
        :return:
        """
        self.running = False
        if self.t is not None:
            self.t.join()

    def _start_connections(self, host, port):
        server_addr = (host, port)
        print(f"Starting connection to {server_addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(sock, events)

    def _service_connection(self, key, mask):
        sock = key.fileobj
        if mask & selectors.EVENT_READ:
            recv_data = ""
            try:
                size = struct.unpack("i", sock.recv(struct.calcsize("i")))[0]
                while len(recv_data) < size:
                    msg = sock.recv(size - len(recv_data))
                    if not msg:
                        break
                    recv_data += msg.decode('utf-8')
            except:
                pass
            if recv_data != "":
                jsondata = None
                try:
                    jsondata = json.loads(recv_data)
                except:
                    pass
                if jsondata is not None:
                    if "type" in jsondata.keys() and "payload" in jsondata.keys():
                        self.callback(jsondata, self.sendData)
            if not recv_data:
                print(f"Closing connection ")
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            while not self.sendQueue.empty():
                msg = self.sendQueue.get().encode("utf-8")
                datasend = struct.pack("i", len(msg)) + msg
                sent = sock.send(datasend)

    def _run(self):
        self.sel = selectors.DefaultSelector()
        self._start_connections(self.host, self.port)

        try:
            while self.running:
                events = self.sel.select(timeout=1)
                if events:
                    for key, mask in events:
                        self._service_connection(key, mask)
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    print("Closing")
                    break
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

