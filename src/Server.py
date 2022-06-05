import sys
import socket
import selectors
import types
from threading import Thread
from queue import Queue, Empty
import json
import struct

def actionHandler(name, payload, server):
    if name in server.playerNames:
        server.queues[name].put(payload)

def gameControlHandler(name, payload, server):
    if name==server.masterName:
        server.queues[name].put(payload)

class MultiSocketServer:
    def __init__(self, ip, port, masterName, playerNames):
        self.host = ip
        self.port = port
        self.t = None
        self.masterName = masterName
        self.playerNames = playerNames
        self.missingPlayers = playerNames.copy()

        self.sendQueues = {}

        self.eventHandlers = {}
        self.eventHandlers["SetAction"] = actionHandler
        self.eventHandlers["GameControl"] = gameControlHandler

        self.queues = {}
        for name in self.playerNames + [self.masterName, ]:
            self.queues[name] = Queue()
            self.sendQueues[name] = Queue()

    def resetQueues(self):
        for name, queue in self.queues.items():
            with queue.mutex:
                queue.queue.clear()

        for name, queue in self.sendQueues.items():
            with queue.mutex:
                queue.queue.clear()

    def start(self):
        self.running = True
        self.t = Thread(target=self._run)
        self.t.start()

    def stop(self):
        self.running = False
        if self.t is not None:
            self.t.join()

    def readData(self, data, name):
        #print(data)
        try:
            datacls = json.loads(data)
        except:
            self.sendData("JSON parsing error", name)
            return None, None, None
        if "command" not in datacls.keys() or "name" not in datacls.keys() or "payload" not in datacls.keys():
            self.sendData("One of the following fields are missing: 'command', 'name', 'payload'", name)
            return None, None, None
        else:
            return datacls["command"], datacls["name"], datacls["payload"]

    def sendData(self, data, name):
        if name == "all":
            for key, queue in self.sendQueues.items():
                queue.put(data)
        elif name in self.sendQueues.keys():
            self.sendQueues[name].put(data)

    def getLatestForName(self, name):
        if name in self.playerNames + [self.masterName, ]:
            if self.queues[name].empty():
                return None
            else:
                action = None
                while not self.queues[name].empty():
                    action = self.queues[name].get()
                return action

    def getGameMasterFIFO(self):
        try:
            return self.queues[self.masterName].get(timeout=0.03)
        except Empty:
            return None

    def checkMissingPlayers(self):
        if len(self.missingPlayers)>0:
            return True
        else:
            return False

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"", name=None)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
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
                command, name, payload = self.readData(recv_data, data.name)
                if command in self.eventHandlers.keys():
                    self.eventHandlers[command](name, payload, self)

                if command == "SetName" and name is not None and name != "all":
                    data.name = name
                    if name in self.missingPlayers:
                        print(name,"connected!")
                        self.missingPlayers.remove(name)

            else:
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.name is not None and data.name in self.sendQueues.keys():
                while not self.sendQueues[data.name].empty():
                    msg = self.sendQueues[data.name].get().encode("utf-8")
                    data.outb = struct.pack("i", len(msg)) + msg
                    sent = sock.send(data.outb)  # Should be ready to write

    def _run(self):
        self.sel = selectors.DefaultSelector()
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print(f"Listening on {(self.host, self.port)}")
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)

        try:
            while self.running:
                events = self.sel.select(timeout=1)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()
