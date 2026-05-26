
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, HorizontalGroup, Vertical
from textual.message import Message
from textual import on
from textual.widgets import Header, Footer, Button, Static
import chess

import websockets
import json

WS_URL = "wss://suyashk13-terminal-chess-backend.hf.space/ws"

class GameStartedMessage(Message):
    def __init__(self, color : str):
        self.color = color
        super().__init__()

class GameOverMessage(Message):
    def __init__(self, winner : str):
        self.winner = winner
        super().__init__()

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
            piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"

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

class CapturedPanel(Static):
    def __init__(self, title : str, team_color : chess.Color, id : str):
        super().__init__(id=id)
        self.title = title
        self.team_color = team_color
    
    def update_panel(self, captured_pieces : list[chess.Piece]):
        sort_order = {chess.QUEEN: 0, chess.ROOK: 1, chess.BISHOP: 2, chess.KNIGHT: 3, chess.PAWN: 4}
        sorted_pieces = sorted(captured_pieces, key=lambda p: sort_order.get(p.piece_type, 5))

        # Format the defeated pieces with your existing custom colors
        piece_strs = []
        for piece in sorted_pieces:
            piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"
            piece_strs.append(f"[{piece_color}]{piece.unicode_symbol()}[/]")

        # Wrap text so it stacks nicely
        captured_text = " ".join(piece_strs)
        self.update(f"[b]{self.title}[/b]\n\n{captured_text}")
    
    def on_mount(self):
        self.update(f"[b]{self.title}[/b]\n\n")


class ChessBoard(Vertical):
    def __init__(self):
        super().__init__()
        self.board = chess.Board()
        self.selected_square = None
        self.legal_moves = []
        self.player_color = None

        # store captured pieces for both teams
        self.captured_by_white = []
        self.captured_by_black = []

    def highlight_check(self):
        """find if a king is in check and highlight the square"""

        # clear previous check highlights
        for square in self.query(Square):
            square.remove_class("-in-check")
        
        if self.board.is_check():
            king_square = self.board.king(self.board.turn)

            # find the specific square widget and add css
            for square in self.query(Square):
                if square.square_index == king_square:
                    square.add_class("-in-check")

    def apply_move(self,move_uci):
        move = chess.Move.from_uci(move_uci)

        # detect captures before pushing the move
        captured_piece = None

        # handle the special en passant case
        if self.board.is_en_passant(move):
            captured_piece = chess.Piece(chess.PAWN, not self.board.turn)
        else:
            captured_piece = self.board.piece_at(move.to_square)

        # add the piece to correct list
        if captured_piece:
            if captured_piece.color == chess.WHITE:
                self.captured_by_black.append(captured_piece)
            else:
                self.captured_by_white.append(captured_piece)

        self.board.push(move)
        
        for square in self.query(Square):
            square.refresh_piece()
        
        # update captured panels after every move
        self.app.query_one("#top_captured", CapturedPanel).update_panel(self.captured_by_black)
        self.app.query_one("#bottom_captured", CapturedPanel).update_panel(self.captured_by_white)

        # check hightlight after every move
        self.highlight_check()

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
            # Second click
            if square in self.legal_moves:
                # 1. Check if the moving piece is a pawn
                moving_piece = self.board.piece_at(self.selected_square)
                is_promotion = False

                if moving_piece and moving_piece.piece_type == chess.PAWN:
                    # 2. Check if it is landing on the 1st rank (0) or 8th rank (7)
                    if chess.square_rank(square) == 0 or chess.square_rank(square) == 7:
                        is_promotion = True
                
                # 3. Create the move ( attach the Queen if its a promotion)
                if is_promotion:
                    move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)
                else:
                    move = chess.Move(self.selected_square, square)
                
                # 4. Push the move to the board
                self.apply_move(move.uci())
                self.app.run_worker(self.app.send_move(move), exclusive=False)

            # reset selection
            self.selected_square = None
            self.legal_moves = []
    
        for square_widget in self.query(Square):
            square_widget.update_style(self.selected_square, self.legal_moves)
        
            # square_widget.refresh_piece()
    
    def reset_board(self):
        """Clear local state and redraw the starting pieces"""
        self.board.reset()
        self.selected_square = None
        self.legal_moves = []
        self.player_color = None

        self.captured_by_white = []
        self.captured_by_black = []

        for square in self.query(Square):
            square.update_style(None, [])
            square.refresh_piece()
        
        self.app.query_one("#top_captured", CapturedPanel).update_panel(self.captured_by_black)
        self.app.query_one("#bottom_captured", CapturedPanel).update_panel(self.captured_by_white)

        self.highlight_check()
    
    def compose(self) -> ComposeResult:

        # 1. Top Section: the 8x8 board and the 1-8 numbers
        with Horizontal(id="board_and_ranks"):

            # The bordered 8x8 playing area
            with Grid(id="inner_board"):
                for rank in range(7,-1,-1):
                    for file in range(8):
                        square = chess.square(file, rank)
                        is_light = (rank + file) % 2 == 0

                        yield Square(self.board, square, is_light)
                
            # The numbers 1-8 on the right
            with Vertical(id="rank_labels"):
                for rank in range(7,-1,-1):
                    yield Static(chess.RANK_NAMES[rank], classes = "label")
        
        # Bottom Section: The letters a-h
        with Horizontal(id="file_labels"):
            for file in range(8):
                yield Static(chess.FILE_NAMES[file], classes = "label")  
            
        
        
class ButtonHandler(Vertical):
    def on_button_pressed(self, event: Button.Pressed):
        layout = self.app.query_one("#main_layout")


        if event.button.id == "start" or event.button.id == "new_game":
            layout.add_class("started")
            layout.remove_class("game_over")

            # update the text label
            status = self.query_one("#status_label", Static)
            status.update("Searching for opponent...")

            # if they click on new game, reset the board pieces locally
            if event.button.id == "new_game":
                board = self.app.query_one(ChessBoard)
                board.reset_board()

            self.app.run_worker(self.app.send_init(), exclusive=False)

        elif event.button.id == "resigned":
            layout.remove_class("started")
            self.app.run_worker(self.app.send_resign(), exclusive=False)
            
    def compose(self) -> ComposeResult:
        yield Static("Welcome to Terminal Chess", id="status_label")
        yield Button("Start Game", id="start", variant="success")
        yield Button("Resign", id="resigned", variant='error')
        yield Button("New Game", id="new_game", variant="primary")


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
        self.ws = await websockets.connect(
            WS_URL,
            ping_interval=20,
            ping_timeout=20,
            )
        await self.listen()
    
    async def send_init(self):
        if self.ws is None:
            self.notify("Still connecting to server. Please wait a moment and try again!", severity="warning")
            # Revert the UI state since we failed to search for an opponent
            layout = self.query_one("#main_layout")
            layout.remove_class("started")
            self.query_one("#status_label", Static).update("Welcome to Terminal Chess")
            return
            
        await self.ws.send(json.dumps({
            "type" : "init_game"
        }))
    
    async def send_move(self, move):
        if self.ws is None: return
        await self.ws.send(json.dumps({
            "type": "move",
            "move": move.uci()
        }))
    
    async def send_game_over(self, winner):
        if self.ws is None: return
        await self.ws.send(json.dumps({
            "type": "game_over",
            "winner": winner
        }))

    async def send_resign(self):
        if self.ws is None: return
        await self.ws.send(json.dumps({
            "type" : "resign"
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
            # self.log("Game Started you are", msg["color"])
            self.post_message(GameStartedMessage(msg["color"]))
        
        elif msg["type"] == "move":
          self.post_message(OpponentMove(msg["move"]))
          
        elif msg["type"] == "game_over":
            self.post_message(GameOverMessage(msg["winner"]))
            
    @on(OpponentMove)
    def update_board(self, event : OpponentMove):
        board = self.query_one(ChessBoard)
        board.apply_move(event.move_uci)

    @on(GameStartedMessage)
    def on_game_start(self, event : GameStartedMessage):
        status = self.query_one("#status_label", Static)
        status.update(f"Game Started!, You are playing [b]{event.color}[/b]")

    @on(GameOverMessage)
    def on_game_over(self, event : GameOverMessage):
        # announce the winner
        status = self.query_one("#status_label", Static)
        status.update(f"[b]Game Over![/b]\nWinner: {event.winner.capitalize()}")

        layout = self.query_one("#main_layout")
        layout.remove_class("started")
        layout.add_class("game_over")


    def on_mount(self):
       self.run_worker(self.connect_ws(), exclusive=True)
      
     
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Vertical(
            # added left panel (white pieces lost)
            CapturedPanel("Captured by Black", chess.WHITE, id="top_captured"),
            CapturedPanel("Captured by White", chess.BLACK, id="bottom_captured"),
            id="left_panels"
            ),
            ChessBoard(),
            ButtonHandler(),
            id="main_layout"
        )
        
    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

def run_app():
    app = ChessApp()
    app.run()

if __name__ == "__main__":
    run_app()