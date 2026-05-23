from fastapi import WebSocket

from game import Game
import messages


class GameManager:
    games: list[Game]
    pendingUser: WebSocket | None
    users: list[WebSocket]

    def __init__(self):
        self.games = []
        self.pendingUser = None
        self.users = []

    async def add_user(self, websocket: WebSocket):
        await websocket.accept()
        self.users.append(websocket)
        await self.add_handler(websocket)

    async def remove_user(self, websocket: WebSocket):
        if self.pendingUser == websocket:
            self.pendingUser = None
        else:
            self.users.remove(websocket)
            for game in self.games:
                if game.player1 == websocket or game.player2 == websocket:
                    self.games.remove(game)

    async def add_handler(self, websocket: WebSocket):
        while True:
            message = await websocket.receive_json()
            print("new move\n ", message)
            if message["type"] == messages.INIT_GAME:
                if self.pendingUser is not None:  # if a users exists
                    # start a game
                    game = Game(self.pendingUser, websocket)
                    await game.start()
                    self.games.append(game)
                    self.users.append(self.pendingUser)
                    self.pendingUser = None
                else:
                    self.pendingUser = websocket
        
            if message["type"] == messages.MOVE:
                game = self.find_game(websocket)
                print(game)
                if game:
                    print("inside make move")
                    await game.make_move(websocket, message["move"])
                
            if message["type"] == messages.GAME_OVER:
                print("reached game over")
                game = self.find_game(websocket)
                if game:
                    self.games.remove(game)
                    print("game removed")
                    print(message)

    def find_game(self, websocket: WebSocket):
        for game in self.games:
            if game.player1 == websocket or game.player2 == websocket:
                return game
