
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, HorizontalGroup
from textual.message import Message
from textual import on
from textual.widgets import Header, Footer, Button, Static
import chess

import websockets
import json

WS_URL = "ws://localhost:8000/ws"

class Square(Static):
    
    def __init__(self,board, square_index : int, is_light: bool):
        super().__init__(expand=True)
        self.square_index = square_index
        self.is_light = is_light
        self.board = board
        
        
    class Clicked(Message):
        def __init__(self, square_index : int):
            self.square_index = square_index
            super().__init__()
    
    def update_style(self, selected, legal):
        self.remove_class("-selected")
        self.remove_class('-legal')
        
        if self.square_index == selected:
            self.add_class("-selected")
        elif self.square_index in legal:
            self.add_class("-legal")
    
    def refresh_piece(self):
        piece = self.board.piece_at(self.square_index)
        if piece:
            piece_color = "#A6ACA5" if piece.color == chess.WHITE else "#4D4848"

            self.update(f"[{piece_color}]{piece.unicode_symbol()}[/]")
        else:
            self.update("")
    

    def on_click(self):
        self.post_message(self.Clicked(self.square_index))
        
    def on_mount(self) -> None:
        if self.is_light:
            self.add_class("-light")
        else:
            self.add_class("-dark")

        # Draw the initial piece
        self.refresh_piece()


class ChessBoard(Grid):
    def __init__(self):
        super().__init__()
        self.board = chess.Board()
        self.selected_square = None
        self.legal_moves = []
        self.player_color = None
        
    def apply_move(self,move_uci):
        move = chess.Move.from_uci(move_uci)
        self.board.push(move)
        
        for square in self.query(Square):
            square.refresh_piece()
    
    def on_square_clicked(self, message : Square.Clicked):
        square = message.square_index
        
        # First click
        if self.selected_square is None:
            piece = self.board.piece_at(square)
            
            if piece is None:
                return # clicked empty square
            
            #enforce turn
            if piece.color != self.board.turn:
                return
            
            if (self.player_color == "white" and not self.board.turn) or (self.player_color == "black" and self.board.turn):
               return   
            
            self.selected_square = square
            
            #get legal moves for this square
            self.legal_moves = [
                move.to_square for move in self.board.legal_moves if move.from_square == square
            ]
            
        else:
            if square in self.legal_moves:
                move = chess.Move(self.selected_square, square)
                self.apply_move(move.uci())
                self.app.run_worker(self.app.send_move(move), exclusive=False)
            
            # reset selection
            self.selected_square = None
            self.legal_moves = []
    
        for square_widget in self.query(Square):
            square_widget.update_style(self.selected_square, self.legal_moves)
        
            # square_widget.refresh_piece()
        
    
    def compose(self) -> ComposeResult:
        for rank in range(7,-1,-1):
            # alphabets at the bottom and numbers at the right
            for file in range(8):
                square = chess.square(file, rank)
                is_light = (rank + file) % 2 == 0
                
                yield Square(self.board, square, is_light)
            
            yield Static(chess.RANK_NAMES[rank], classes = "label")
        
        for file in range(8):
            yield Static(chess.FILE_NAMES[file], classes = "label")  
            
        
        
class ButtonHandler(HorizontalGroup):
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "start":
            self.add_class("started")
            self.app.run_worker(self.app.send_init(), exclusive=False)
        elif event.button.id == "resigned":
            self.remove_class("started")
            self.app.log("You resigned!")
            # You can also send a message to the server if needed
            # self.app.run_worker(self.app.send_resign(), exclusive=False)
            
    def compose(self) -> ComposeResult:
        yield Button("Start Game", id="start", variant="success")
        yield Button("Resign", id="resigned", variant='error')


class OpponentMove(Message):
    def __init__(self, move_uci: str):
        self.move_uci = move_uci
        super().__init__()
            

class ChessApp(App):
    CSS_PATH = "chess.css"
    BINDINGS = [('d', 'toggle_dark', 'Toggle Dark Mode'),
                ]
    
    def __init__(self):
        super().__init__()
        self.ws = None
    
    async def connect_ws(self):
        self.ws = await websockets.connect(WS_URL)
        await self.listen()
    
    async def send_init(self):
        await self.ws.send(json.dumps({
            "type" : "init_game"
        }))
    
    async def send_move(self, move):
        await self.ws.send(json.dumps({
            "type": "move",
            "move": move.uci()
        }))
    
    async def send_game_over(self, winner):
        await self.ws.send(json.dumps({
            "type": "game_over",
            "winner": winner
        }))

    async def listen(self):
        while True:
            data = await self.ws.recv()
            message = json.loads(data)
            
            await self.handle_message(message)
            
    async def handle_message(self, msg):
        board = self.query_one(ChessBoard)
        
        if msg["type"] == "init_game":
            board.player_color = msg["color"]
            self.log("Game Started you are", msg["color"])
        
        elif msg["type"] == "move":
          self.post_message(OpponentMove(msg["move"]))
          
        elif msg["type"] == "game_over":
            self.log("Winner:", msg["winner"])
            
    @on(OpponentMove)
    def update_board(self, event : OpponentMove):
        board = self.query_one(ChessBoard)
        board.apply_move(event.move_uci)

    def on_mount(self):
       self.run_worker(self.connect_ws(), exclusive=True)
      
     
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            ChessBoard(),
            ButtonHandler()
        )
        
    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )
    

if __name__ == "__main__":
    app = ChessApp()
    app.run()