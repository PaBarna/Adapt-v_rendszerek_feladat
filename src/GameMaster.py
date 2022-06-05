import json

from Config import *
from Engine import AdaptIOEngine
from Server import MultiSocketServer
from threading import Timer, Thread
from Gui_Beta import *


class STATE:
    PRERUN = 0
    RUNNING = 1
    WAIT_COMMAND = 2
    WAIT_START = 3

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval) and not self.finished.is_set():
            self.function(*self.args, **self.kwargs)


class GameMaster:
    def __init__(self):
        if DISPLAY_ON:
            self.disp = AdaptIODisplay(self.close)

        playerNames = []
        for n,s in STRATEGY_DICT.items():
            if s=="remoteplayer":
                playerNames.append(n)
        print("Players: ",playerNames)
        self.serv = MultiSocketServer(IP, PORT, GAMEMASTER_NAME, playerNames)
        self.engine = AdaptIOEngine(sender=self.serv.sendData, getter=self.serv.getLatestForName)
        self.tickLength = DEFAULT_TICK_LENGTH_S
        self.timer = RepeatTimer(self.tickLength, self._processTick)
        self.running = False
        self.gameState = STATE.PRERUN
        self.pollGameCommands = True
        self.exitTimer = None
        self.gameStartTimer = None
        self.autoStartTimer = None
        self.canStart = False

    def _startGame(self):
        self.gameState = STATE.RUNNING
        self.serv.sendData(json.dumps({"type": "started", "payload": {"tickLength": self.tickLength}}), "all")
        self.engine.sendObservations()


    def _processTick(self):
        if self.gameState == STATE.PRERUN:
            if self.autoStartTimer is None:
                self.autoStartTimer = Timer(WAIT_FOR_JOIN, self._startGame)
                self.autoStartTimer.start()
            if not self.serv.checkMissingPlayers():
                self._startGame()

        elif self.gameState == STATE.RUNNING:
            if self.autoStartTimer is not None:
                self.autoStartTimer.cancel()
                self.autoStartTimer = None
            if not self.engine.tick():
                self.gameState = STATE.WAIT_COMMAND
                self.serv.sendData(json.dumps({"type":"leaderBoard","payload":self.engine.getLeaderboard()}),"all")
            else:
                if DISPLAY_ON:
                    self.disp.updateDisplayInfo(*self.engine.generateDisplayData())

        elif self.gameState == STATE.WAIT_COMMAND:
            if self.exitTimer is None:
                self.exitTimer = Timer(30, self.close)
                self.exitTimer.start()

        elif self.gameState == STATE.WAIT_START:
            if self.exitTimer is not None:
                self.exitTimer.cancel()
                self.exitTimer = None

            if self.canStart:
                self.gameState = STATE.RUNNING
                self.canStart = False

        else:
            pass

    def __changeTickLength(self, newInterval):
        # self.running currently not updated properly. Do NOT use without a revision!
        if self.running:
            self.timer.cancel()
            self.tickLength = newInterval
            self.timer = RepeatTimer(self.tickLength, self._processTick)
            self.timer.start()
        else:
            self.tickLength = newInterval
            self.timer = RepeatTimer(self.tickLength, self._processTick)

    def close(self):
        self.serv.sendData(json.dumps({"type": "serverClose", "payload": None}), "all")
        self.timer.cancel()
        self.timer.join()
        self.pollGameCommands = False
        self.serv.stop()
        if self.exitTimer is not None:
            self.exitTimer.cancel()
        if self.autoStartTimer is not None:
            self.autoStartTimer.cancel()
        if DISPLAY_ON:
            self.disp.kill()
        if LOG:
            self.engine.closeLog()
        print("Close finished")

    def run(self):
        self.serv.start()
        self.timer.start()
        self.running = True
        try:
            while self.pollGameCommands:
                if DISPLAY_ON:
                    self.disp.launchDisplay(self.close)

                action = self.serv.getGameMasterFIFO()
                if action is None:
                    continue
                if not ("type" in action.keys() and "data" in action.keys()):
                    continue
                if action["type"] == "interrupt":
                    self.close()
                if action["type"] == "start":
                    self.canStart = True
                    self.serv.sendData(json.dumps({"type": "started", "payload": {"tickLength":self.tickLength}}), "all")
                    self.engine.sendObservations()
                if action["type"] == "reset":
                    if self.gameState != STATE.RUNNING:
                        self.canStart = False
                        self.engine.reset_state(action["data"]["mapPath"], action["data"]["updateMapPath"])
                        self.serv.sendData(json.dumps({"type": "readyToStart", "payload": None}), "all")
                        self.gameState = STATE.WAIT_START
        except KeyboardInterrupt:
            print("Interrupted, stopping")
            self.close()