from enum import Enum

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    ResultUser,
    RoomInfo,
    RoomUser,
    SafeUser,
    WaitRoomStatus,
    end_room,
    get_result,
    join_room,
    leave_room,
    start_room,
    wait_room,
)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)  # 認証失敗
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def user_update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    model.update_user(token, req.user_name, req.leader_card_id)
    return {}


class RoomCreateRequest(BaseModel):
    live_id: int
    select_difficulty: LiveDifficulty


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: RoomCreateRequest, token: str = Depends(get_auth_token)):
    """新しい部屋の生成"""
    room_id = model.create_room(token, req.live_id, req.select_difficulty.value)
    return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: list[RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest):
    """入場可能なルーム一覧を取得"""
    room_info_list = model.get_room_info(req.live_id)
    return RoomListResponse(room_info_list=room_info_list)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty


class RoomJoinResponse(BaseModel):
    join_room_result: JoinRoomResult


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)):
    """取得した内のどれかのルームに入場を試みる"""
    join_room_result = join_room(token, req.room_id, req.select_difficulty.value)
    return RoomJoinResponse(join_room_result=join_room_result)


class RoomWaitRequest(BaseModel):
    room_id: int


class RoomWaitResponse(BaseModel):
    status: WaitRoomStatus
    room_user_list: list[RoomUser]


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    """ルーム待機中"""
    res = wait_room(token, req.room_id)
    return RoomWaitResponse(status=res[0], room_user_list=res[1])


class RoomStartRequest(BaseModel):
    room_id: int


@app.post("/room/start", response_model=Empty)
def room_start(req: RoomStartRequest, token: str = Depends(get_auth_token)):
    """ルームのライブ開始, ホストが叩く"""
    start_room(token, req.room_id)
    return {}


class RoomEndRequest(BaseModel):
    room_id: int
    judge_count_list: list[int]
    score: int


@app.post("/room/end", response_model=Empty)
def room_end(req: RoomEndRequest, token: str = Depends(get_auth_token)):
    """ルームのライブ終了, 各メンバーが叩く"""
    end_room(token, req.room_id, req.judge_count_list, req.score)
    return {}


class RoomResultRequest(BaseModel):
    room_id: int


class RoomResultResponse(BaseModel):
    result_user_list: list[ResultUser]


@app.post("/room/result", response_model=RoomResultResponse)
def room_result(req: RoomResultRequest, token: str = Depends(get_auth_token)):
    """結果を受け取る"""
    result_user_list = get_result(token, req.room_id)
    return RoomResultResponse(result_user_list=result_user_list)


class RoomLeaveRequest(BaseModel):
    room_id: int


@app.post("/room/leave", response_model=Empty)
def room_leave(req: RoomLeaveRequest, token: str = Depends(get_auth_token)):
    """ルームを退出する, ホストが叩く場合は適当な同じ部屋のユーザーをホストにする"""
    leave_room(token, req.room_id)
    return {}
