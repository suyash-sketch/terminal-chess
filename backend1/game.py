from fastapi import WebSocket
import time
import chess
import messages

class Game:
    player1 : WebSocket
    player2 : WebSocket
    board : chess.Board
    start_time : time.time

    def __init__(self, player1 : WebSocket, player2 : WebSocket):
        self.player1 = player1
        self.player2 = player2
        self.board = chess.Board()
        self.start_time = time.time()
    
    async def start(self):
        await self.player1.send_json({
            "type" : messages.INIT_GAME,
            "color" : "white"
        })

        await self.player2.send_json({
            "type" : messages.INIT_GAME,
            "color" : "black"
        })
    

    async def make_move(self, websocket : WebSocket, move: str):
        #validation here
        # Is it this users move
        # is the move valid
        
        #if board.turn is True it means whites turn, if it is False it means blacks turn  
        current_player = self.player1 if self.board.turn else self.player2
        if websocket != current_player:
            return
            
        print("did not early return")

        try:
            move_obj = chess.Move.from_uci(move)
        except ValueError as e:
            print(e)
            return #invalid format
        
        if move_obj not in self.board.legal_moves:
            return #illegal move
        
        self.board.push(move_obj)
        print("move succeeded")
        # check if the game is over
        if self.board.is_game_over():
            result = self.board.result() #e.g 1-0, 0-1, 1/2-1/2

            if result == "1-0":
                winner = "white"
            elif result == "0-1":
                winner = 'black'
            else:
                winner = "draw"

            message = {
                "type" : messages.GAME_OVER,
                "winner" : winner
            }            
            print("game over :" + winner)
            
            if self.board.turn:
                print("player 2 won sending move to player 1")
                await self.player1.send_json({
                    "type" : messages.MOVE,
                    "move" : move_obj.uci()
                })
            else:
                print("player 1 won sending move to player 2")
                await self.player2.send_json({
                    "type" : messages.MOVE,
                    "move" : move_obj.uci()
                })


            await self.player1.send_json(message)
            await self.player2.send_json(message)

            return

        #if the game is not over then update and tell the next player to move
        print("Next Turn:", "white" if self.board.turn else "black")
        #white player sends move to black player
        if not self.board.turn:
            print("sending to player 2\n")
            await self.player2.send_json({
                "type" : messages.MOVE,
                "move" : move_obj.uci()
            })
        else:
            # black player sends move to white player
            print("sending to player 1\n")
            await self.player1.send_json({
                "type" : messages.MOVE,
                "move" : move_obj.uci()
            })

        # await self.player1.send_json({
        #     "type" : messages.MOVE,
        #     "move" : move_obj.uci()
        # })
        # await self.player2.send_json({
        #     "type" : messages.MOVE,
        #     "move" : move_obj.uci()
        # })

        # send the updated board to both players


    # resign logic
    async def handle_resign(self, websocket: WebSocket):
        if websocket == self.player1:
            winner = "black"
        else:
            winner = "white"
        
        message = {
            "type" : messages.GAME_OVER,
            "winner" : winner,
            "reason" : "resignation"
        }
        print(f"{message}\n")
        await self.player1.send_json(message)
        await self.player2.send_json(message)