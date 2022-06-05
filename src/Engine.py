import numpy as np
from collections import Counter
import random
from Player import *
from Config import *
import os
from datetime import datetime

class AdaptIOEngine:
    neighbourDifferencies = {0: np.array([0, 1]), 1: np.array([0, -1]), 2: np.array([1, 0]), 3: np.array([-1, 0])}

    @staticmethod
    def getRandomNeighbor(pos):
        r = random.randint(0, 3)
        if r == 0:
            return pos + np.array([0, 1])
        elif r == 1:
            return pos + np.array([0, -1])
        elif r == 2:
            return pos + np.array([1, 0])
        elif r == 3:
            return pos + np.array([-1, 0])

    def __init__(self, **kwargs):
        self.mapPath = MAPPATH
        self.fieldupdate_path = FIELDUPDATE_PATH
        self.field, self.size = self.prepareField(self.mapPath)
        self.field_old = self.field.copy()
        self.foodgen_map, _ = self.prepareField(self.fieldupdate_path)
        self.foodgen_map_old = self.foodgen_map.copy()
        self.startField = self.field
        self.startingSize = STARTING_SIZE
        self.minRatio = MIN_RATIO
        self.visionRange = VISION_RANGE
        self.updateMode = UPDATE_MODE
        self.visibilityMask = self.genVisibilityMask()
        self.ticknum = 0
        self.strategyDict = STRATEGY_DICT

        self.log = LOG
        self.logpath = ' '
        self.logname = ' '

        if self.log:
            self.setLog()

        ids = list(range(4))
        random.shuffle(ids)

        self.players = [
            Player(list(self.strategyDict.keys())[i], list(self.strategyDict.values())[i], self.startingSize, **kwargs)
            for i in
            range(4)]

        diffFromSide = DIFF_FROM_SIDE
        self.players[ids[0]].pos = np.array([0 + diffFromSide, 0 + diffFromSide])
        self.players[ids[1]].pos = np.array([self.size - diffFromSide - 1, 0 + diffFromSide])
        self.players[ids[2]].pos = np.array([0 + diffFromSide, self.size - diffFromSide - 1])
        self.players[ids[3]].pos = np.array([self.size - diffFromSide - 1, self.size - diffFromSide - 1])

    def setLog(self):
        self.logpath = LOG_PATH
        logname = 'adaptio_log_' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S' + '.txt')

        try:
            os.makedirs(self.logpath, exist_ok=True)
            self.logfile = open(os. path. join(self.logpath, logname), "a")
            print("Log directory and file is ready!")
        except OSError as error:
            print("Log directory can not be created!")

    def writeLog(self, ticknum, actions, field, players):
        players_info = []
        for player in players:
            players_info.append({"name":player.name,"pos":player.pos.tolist(),"size":player.size})


        self.logfile.write(json.dumps({"tick:":ticknum,"actions":actions,"player_info":players_info,"field":field.tolist() })+"\n")

    def closeLog(self):
        self.logfile.close()
        print("Log closed!")

    def genVisibilityMask(self):
        coordlist = []
        for i in np.arange(-self.visionRange, self.visionRange + 1):
            for j in np.arange(-self.visionRange, self.visionRange + 1):
                if np.sqrt(i ** 2 + j ** 2) <= self.visionRange:
                    coordlist.append((int(i), int(j)))

        return coordlist

    def prepareField(self, mapPath):
        field = np.transpose(np.loadtxt(mapPath))
        size = field.shape[0]
        return field, size

    def checkBound(self, pos):
        if not 0 <= pos[0] < self.size or not 0 <= pos[1] < self.size:
            return False
        if self.field[pos[0], pos[1]] == 9:
            return False
        else:
            return True

    def makeAction(self, action, pos):
        oldpos = pos.copy()
        if action == "0":
            return pos
        if action[0] == "-":
            pos[0] -= 1
        if action[0] == "+":
            pos[0] += 1
        if action[1] == "-":
            pos[1] -= 1
        if action[1] == "+":
            pos[1] += 1

        if not self.checkBound(pos):
            pos = oldpos
        return pos.copy()

    def handleCollision_randomized(self, positions, oldPositions, valueToHandle):
        newpos = positions.copy()
        displacements = list(self.neighbourDifferencies.values())
        random.shuffle(displacements)

        colliding = []
        for i in range(len(positions)):
            if positions[i] == valueToHandle:
                colliding.append(i)

        sizes = np.array([self.players[i].size for i in colliding])
        idx = np.argsort(sizes)
        if sizes[idx[0]] >= sizes[idx[1]] * self.minRatio:
            newsize = np.sum(sizes)
            colliding.remove(colliding[idx[0]])
            for dead in colliding:
                self.players[dead].die()

            self.players[idx[0]].size = newsize

        else:
            j = 0
            for i in colliding:
                newpos[i] += displacements[j]
                j += 1
        return newpos

    def handleCollision_oldpos(self, positions, oldPositions, valueToHandle):
        newpos = positions.copy()

        colliding = []
        for i in range(len(positions)):
            if tuple(positions[i]) == tuple(valueToHandle):
                colliding.append(i)

        sizes = np.array([self.players[i].size for i in colliding])
        idx = np.argsort(sizes)[::-1]
        if sizes[idx[0]] >= sizes[idx[1]] * self.minRatio:
            newsize = np.sum(sizes)
            self.players[colliding[idx[0]]].size = newsize
            colliding.remove(colliding[idx[0]])
            for dead in colliding:
                self.players[dead].die()

        else:
            for i in colliding:
                newpos[i] = oldPositions[i].copy()
        return newpos

    def getLeaderboard(self):
        playerData = []
        for player in self.players:
            playerData.append({"name":player.name,"active":player.active,"maxSize":player.size})

        return {"ticks":self.ticknum, "players":playerData}

    def surveyArea(self, player):
        pos = player.pos
        leaderBoard = self.getLeaderboard()
        observation = {"pos": pos.tolist(), "tick": self.ticknum, "active": player.active, "size": player.size,
                       "vision": [], "leaderBoard":leaderBoard}
        playerpos = [tuple(player.pos) for player in self.players]
        for diffcoord in self.visibilityMask:
            vispos = pos + np.array(diffcoord)
            if tuple(vispos) in playerpos:
                playerIdx = playerpos.index(tuple(vispos))
                if self.players[playerIdx].active:
                    playerDict = {}
                    playerDict["size"] = self.players[playerpos.index(tuple(vispos))].size
                    playerDict["name"] = self.players[playerpos.index(tuple(vispos))].name
                else:
                    playerDict = None
            else:
                playerDict = None

            if not 0 <= vispos[0] < self.size or not 0 <= vispos[1] < self.size:
                val = 9
            else:
                val = self.field[int(vispos[0]), int(vispos[1])]
            observation["vision"].append({"relative_coord": diffcoord, "value": val, "player": playerDict})
        return observation

    def updatePlayers(self, newpos):
        for i in range(len(self.players)):
            if not self.players[i].active:
                continue
            self.players[i].pos = newpos[i]
            if 0 < self.field[newpos[i][0], newpos[i][1]] <= 3:
                self.players[i].size += self.field[newpos[i][0], newpos[i][1]]
                self.field[newpos[i][0], newpos[i][1]] = 0

    def updateFood(self):
        if self.updateMode == "static":
            return
        elif self.updateMode == "statistical":
            if (self.ticknum-FOODGEN_OFFSET) % FOODGEN_COOLDOWN == 0 and self.ticknum-FOODGEN_OFFSET>=0:
                random_food = np.random.rand(self.field.shape[0], self.field.shape[1])
                new_food = (self.field < 3) & (self.foodgen_map*FOODGEN_SCALER > random_food)
                self.field = self.field + new_food
        else:
            pass

    def checkCollision(self, newpos, oldpos):
        checked = False
        while not checked:
            checked = True
            positions = [tuple(n) for n in newpos]
            for i in range(4):
                if not self.players[i].active:
                    positions[i] = None
            counts = Counter(positions)
            for collisionTile, cnt in counts.items():
                if cnt > 1 and collisionTile is not None:
                    newpos = self.handleCollision_oldpos(newpos, oldpos, collisionTile)
                    checked = False

        return newpos

    def reset_state(self, mapPath=None, updateMapPath=None):
        if LOG:
            self.closeLog()
            self.setLog()

        self.ticknum = 0
        if mapPath is None:
            self.field = self.field_old.copy()
        else:
            self.field, self.size = self.prepareField(mapPath)
            self.field_old = self.field.copy()

        if updateMapPath is None:
            self.foodgen_map = self.foodgen_map_old.copy()
        else:
            self.foodgen_map, _ = self.prepareField(updateMapPath)
            self.foodgen_map_old = self.foodgen_map.copy()

        ids = list(range(4))
        random.shuffle(ids)

        diffFromSide = DIFF_FROM_SIDE
        self.players[ids[0]].pos = np.array([0 + diffFromSide, 0 + diffFromSide])
        self.players[ids[1]].pos = np.array([self.size - diffFromSide - 1, 0 + diffFromSide])
        self.players[ids[2]].pos = np.array([0 + diffFromSide, self.size - diffFromSide - 1])
        self.players[ids[3]].pos = np.array([self.size - diffFromSide - 1, self.size - diffFromSide - 1])

        for i in range(4):
            self.players[i].size = STARTING_SIZE
            self.players[i].reset()

    def check_conditions(self):
        if self.ticknum >= MAXTICKS > 0:
            return True
        alive = 0
        for i in range(4):
            if self.players[i].active:
                alive += 1
        if not SOLO_ENABLED and alive == 1:
            return True
        if alive == 0:
            return True

    def generateDisplayData(self):
        return self.ticknum, self.players.copy(), self.field.copy()

    def sendObservations(self):
        for i in range(len(self.players)):
            self.players[i].strategy.setObservations(self.players[i], self.surveyArea(self.players[i]))

    def tick(self):
        if self.check_conditions():
            return False

        actions = [player.strategy.getNextAction() for player in self.players]
        pos = [player.pos.copy() for player in self.players]

        newpos = []
        for i in range(len(self.players)):
            if not self.players[i].active:
                newpos.append(pos[i].copy())
            else:
                newpos.append(self.makeAction(actions[i], pos[i].copy()))

        newpos = self.checkCollision(newpos, pos)
        self.updatePlayers(newpos)
        self.updateFood()
        if(self.log):
            self.writeLog(self.ticknum, actions, self.field, self.players)
        self.ticknum += 1
        self.sendObservations()

        return True