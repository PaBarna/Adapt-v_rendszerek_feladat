import time
import numpy as np
import pygame
from threading import Thread
from Player import Player
from Config import *

# Convert Numbers to Colors
numTOcolor = {
    EMPTY:    BACK_COLOR,
    LOW:      LOW_COLOR,
    MID:      MID_COLOR,
    HIGH:     HIGH_COLOR,
    PLAYER_1: PLAYER_1_COLOR,
    PLAYER_2: PLAYER_2_COLOR,
    PLAYER_3: PLAYER_3_COLOR,
    PLAYER_4: PLAYER_4_COLOR,
    WALL:     WALL_COLOR,
}

def gui(displayObj):
    """
    Running display loop.
    """
    displayObj.launch()

class AdaptIODisplay():
    """
    Contains the essential game gui elements.
    """
    def __init__(self, closeFunction):
        """
        Initialize AdaptIO class.
        """
        pygame.init()
        self.closeFunction = closeFunction

        self.load_dummy()
        self.run = True
        self.updated = True
        self.SCREEN = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.CLOCK = pygame.time.Clock()
        pygame.display.set_caption("AdaptIO")
        self.SCREEN.fill(BACK_COLOR)

        # Draw static display elements
        self.drawGrid()

        print('AdaptIO is started!')

    def updateDisplayInfo(self, tick, players, map):
        """
        Update the display object inner variables.
        """
        self.updated = True
        self.tick = tick
        self.map = map
        self.players = players

    def load_dummy(self):
        Player_1 = Player('BOB', 'naivebot', 1)
        Player_1.pos = (1, 1)
        Player_2 = Player('ROB', 'naivebot', 1)
        Player_2.pos = (38, 1)
        Player_3 = Player('ZOD', 'naivebot', 1)
        Player_3.pos = (38, 38)
        Player_4 = Player('POO', 'naivebot', 1)
        Player_4.pos = (1, 38)
        # Player list
        self.players = [Player_1, Player_2, Player_3, Player_4]

        self.map = np.zeros((40,40),dtype=np.int32)
        # Tick
        self.tick = 0

    def updateDisplay(self):
        self.updateTick()
        self.updateMap()
        self.updatePlayers()
        self.updateScoreBoard()

    def launchDisplay(self, callback):
        if self.run:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run = False
                    callback
                    self.closeFunction()
                    print('AdaptIO is closed!')
            if self.updated:
                self.updateDisplay()
                self.updated = False
            if self.run:
                pygame.display.update()
            else:
                pygame.quit()

    def kill(self):
        self.run = False
        print('AdaptIO is closed!')

    def updateMap(self):
        """
        Update the map grid by grid according to the map_actual.
        """
        for x in range(0, BLOCK_NUM):
            for y in range(0, BLOCK_NUM):
                rect = pygame.Rect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + 2, BLOCK_SIZE - 4, BLOCK_SIZE - 4)
                pygame.draw.rect(self.SCREEN, numTOcolor[self.map[x,y]], rect, 0)

    def updatePlayers(self):
        """
        Draw the players on the map.
        """
        for i in range(len(self.players)):
            x = self.players[i].pos[0]
            y = self.players[i].pos[1]
            rect = pygame.Rect(x * BLOCK_SIZE + 2, y * BLOCK_SIZE + 2, BLOCK_SIZE - 4, BLOCK_SIZE - 4)

            if self.players[i].active:
                pygame.draw.rect(self.SCREEN, numTOcolor[i+4], rect, 0)
            else:
                pygame.draw.rect(self.SCREEN, PLAYER_DEAD, rect, 0)

    def drawGrid(self):
        """
        Draw the grid pattern of the map. (static element)
        """
        blockSize = BLOCK_SIZE #Set the size of the grid block
        width     = BLOCK_NUM*BLOCK_SIZE
        height    = BLOCK_NUM*BLOCK_SIZE

        rect = pygame.Rect(BLOCK_NUM * BLOCK_SIZE, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.SCREEN, GRID_COLOR, rect, 0)

        for x in range(0, width, blockSize):
            for y in range(0, height, blockSize):
                rect = pygame.Rect(x, y, blockSize, blockSize)
                pygame.draw.rect(self.SCREEN, GRID_COLOR, rect, 1)

    def updateScoreBoard(self):
        """
        Draw the scoreboard on the GUI. (static element)
        """
        for i in range(0, len(self.players)):
            self.drawPlayerBoard(i, self.players[i].name, self.players[i].size, self.players[i].active)


    def drawBlock(self, num_x, num_y, color):
        """
        Draw one element of the map with the desired color.
        :param num_x: Grid element number from the left.
        :param num_y: Grid element number from the top.
        :param color: Desired color.
        """
        rect = pygame.Rect(num_x*BLOCK_SIZE+2, num_y*BLOCK_SIZE+2, BLOCK_SIZE-4, BLOCK_SIZE-4)
        pygame.draw.rect(self.SCREEN, color, rect, 0)

    def drawPlayerBoard(self, player_id, player_name, player_size, active):
        """
        Draw one Player Board with size and name texts.
        :param x: Top left corner x position
        :param y: Top left corner y position
        :param player_id: player number (1-4)
        :param player_name: name of the player
        :param player_size: size of the player
        """
        x = BLOCK_NUM * BLOCK_SIZE + 2
        y = (5 * BLOCK_SIZE - 4) * (player_id) + player_id * 2

        width = WINDOW_WIDTH - (BLOCK_NUM * BLOCK_SIZE) - 8
        height = (5 * BLOCK_SIZE) - 8
        rect = pygame.Rect(x + 2, y + 2, width, height)
        pygame.draw.rect(self.SCREEN, BOARD_COLOR, rect, 0)
        flag = pygame.Rect(x+8, y+8, 20 , height - 12)
        pygame.draw.rect(self.SCREEN, numTOcolor[player_id+4], flag, 0)

        font = pygame.font.SysFont(None, 30)
        if active:
            state = ' ALIVE'
            state_color = ALIVE_COLOR
        else:
            state = ' DEAD'
            state_color = DEAD_COLOR
        sttr = 'Player ' + str(player_id)
        text_player = font.render(sttr, True, TEXT_COLOR)
        text_name = font.render(player_name, True, TEXT_COLOR)
        text_size = font.render(f'Size: {player_size}', True, TEXT_COLOR)
        text_state = font.render(state, True, state_color)
        self.SCREEN.blit(text_player, (x + 40, y + 8))
        self.SCREEN.blit(text_state, (x + 125, y + 8))
        self.SCREEN.blit(text_name,   (x + 50, y + 8 + 30))
        self.SCREEN.blit(text_size,   (x + 40, y + 8 + 60))

    def updateTick(self):
        """
        Draw the Tick on Display.
        """
        block = pygame.Rect(804, 400, 192, 60)
        pygame.draw.rect(self.SCREEN, BOARD_COLOR, block, 0)
        font = pygame.font.SysFont(None, 40)
        text_tick = font.render(f'Tick: {self.tick}', True, TEXT_COLOR)
        self.SCREEN.blit(text_tick, (830, 420))

# Run the GUI.
if __name__ == '__main__':
    adaptIO = AdaptIODisplay()
    t = Thread(target=gui,args=(adaptIO,))
    t.start()
    time.sleep(10)
    adaptIO.kill()
    t.join()