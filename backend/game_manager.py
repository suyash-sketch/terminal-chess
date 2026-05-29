from fastapi import WebSocket
from typing import Dict
from game import Game
import messages
import random
import string

class GameManager:
    games: list[Game]
    pendingUser: WebSocket | None
    users: list[WebSocket]
    private_room_players : Dict[str,WebSocket]

    def __init__(self):
        self.games = []
        self.pendingUser = None
        self.users = []
        self.private_room_players = {}

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

        for game_id, player in self.private_room_players.items():
            if player == websocket:
                room_to_delete = game_id
                break
        del self.private_room_players[room_to_delete]

    async def add_handler(self, websocket: WebSocket):
        while True:
            message = await websocket.receive_json()
            print("new move\n ", message)

            if message["type"] == messages.ROOM:
                if message.get("game_id") is None:
                    game_id = self.generate_game_id()
                    print("game_id:",game_id)
                    self.private_room_players[game_id] = websocket
                    await websocket.send_json({
                        "type" : "room",
                        "game_id" : game_id
                    })
                else:
                    friend = self.private_room_players.get(message["game_id"])
                    if friend:
                        game = Game(websocket, friend)
                        await game.start()
                        self.games.append(game)

            if message["type"] == messages.INIT_GAME:
                if self.pendingUser is None:
                    self.pendingUser = websocket
                elif self.pendingUser != websocket: # make sure the pending user is not the same as the current user
                    game = Game(self.pendingUser, websocket)
                    await game.start()
                    self.games.append(game)
                    self.pendingUser = None
        
            if message["type"] == messages.MOVE:
                game = self.find_game(websocket)
                print(game)
                if game:
                    print("inside make move")
                    # Capture the return value of make_move
                    is_game_over = await game.make_move(websocket, message["move"])

                    # if make_move returns True, it means the game is over and we should remove it from the list of games
                    if is_game_over:
                        self.games.remove(game)
                        print("Checkmate! Game safely removed from memory.")
                
            if message["type"] == messages.RESIGN:
                print("reached resign")
                game = self.find_game(websocket)
                if game:
                    await game.handle_resign(websocket)
                    self.games.remove(game)
                    print("game resigned")

    def find_game(self, websocket: WebSocket):
        for game in self.games:
            if game.player1 == websocket or game.player2 == websocket:
                return game
    
    def generate_game_id(self):
        letters = string.ascii_letters
        length = 6
        return "".join(random.sample(letters,length))