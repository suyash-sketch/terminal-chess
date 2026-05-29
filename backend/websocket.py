from game_manager import GameManager
# from fastapi import (FastAPI, WebSocket, Cookie, Depends, Query, status, WebSocketException, WebSocketDisconnect)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

game_manager = GameManager()

@app.get("/")
async def root():
    return {"message": "Welcome to the Chess Game WebSocket API!"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await game_manager.add_user(websocket)
    except WebSocketDisconnect:
        await game_manager.remove_user(websocket)