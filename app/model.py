import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine

# from app.api import Live_Difficulty


max_user_count = 4  # 部屋の最大人数


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `user` (name, token, leader_card_id) VALUES (:name, :token, :leader_card_id)"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result.lastrowid)
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    result = conn.execute(
        text("SELECT `id`, `name`, `leader_card_id` FROM `user` WHERE `token`=:token"),
        dict(token=token),
    )  # dict(token=token)は:tokenを置換する用の辞書？
    try:  # 結果が帰ってくる=ユーザーが存在する場合
        row = result.one()
    except NoResultFound:  # ユーザーが存在しない場合
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE `user` SET `name`=:name, `leader_card_id`=:leader_card_id WHERE `token`=:token"
            ),
            dict(token=token, name=name, leader_card_id=leader_card_id),
        )
        # print(result.lastrowid)


class Live_Difficulty(Enum):
    normal = 1
    hard = 2


class JoinRoomResult(Enum):
    OK = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(Enum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int


class RoomUser(BaseModel):
    user_id: int
    name: str
    leader_card_id: int
    select_difficulty: Live_Difficulty
    is_me: bool
    is_host: bool


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list
    score: int


def create_room(token: str, live_id: int, select_difficulty: Live_Difficulty) -> int:
    result = get_user_by_token(token)  # オーナーのidを取得
    user_id = result.id
    with engine.begin() as conn:
        result = conn.execute(  # 部屋の生成
            text("INSERT INTO `room` (`live_id`) VALUES (:live_id)"),
            dict(live_id=live_id),
        )
        room_id = result.lastrowid
        conn.execute(  # オーナーの追加
            text(
                "INSERT INTO `room_member` (`id`, `room_id`, `select_difficulty`, `is_host`) VALUES (:user_id, :room_id, :select_difficulty, 1)"
            ),
            dict(user_id=user_id, room_id=room_id, select_difficulty=select_difficulty),
        )
        return room_id


def get_room_info(live_id: int) -> list:
    with engine.begin() as conn:
        if live_id == 0:  # live_id = 0のとき全てのルームを対象とする
            result = conn.execute(  # 部屋の生成
                text("SELECT `room_id` FROM `room` WHERE `live_id`=:live_id"),
                dict(live_id=live_id),
            )
        else:
            result = conn.execute(  # 部屋の生成
                text("SELECT `room_id` FROM `room` WHERE `live_id`=:live_id"),
                dict(live_id=live_id),
            )
        rows = result.all()
        room_info_list = []
        for row in rows:
            result = conn.execute(  # 部屋の生成
                text("SELECT COUNT(`id`) FROM `room_member` WHERE `room_id`=:room_id"),
                dict(room_id=row.room_id),
            )
            joined_user_count = result.one()["COUNT(`id`)"]
            if joined_user_count == max_user_count:  # 満員のルームを除く
                continue
            room_info_list.append(
                RoomInfo(
                    room_id=joined_user_count,
                    live_id=live_id,
                    joined_user_count=joined_user_count,
                    max_user_count=max_user_count,
                )
            )
        return room_info_list


def join_room(token: str, room_id: int, select_difficulty: int) -> int:
    result = get_user_by_token(token)  # joinするユーザのidを取得
    user_id = result.id
    with engine.begin() as conn:
        result = conn.execute(  # 現在の人数を確認
            text("SELECT COUNT(`id`) FROM `room_member` WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        joined_user_count = result.one()["COUNT(`id`)"]
        if joined_user_count >= 4:
            return 2
        elif joined_user_count == 0:
            return 3
        else:
            conn.execute(
                text(
                    "INSERT INTO `room_member` (`id`, `room_id`, `select_difficulty`) VALUES (:user_id, :room_id, :select_difficulty)"
                ),
                dict(
                    user_id=user_id,
                    room_id=room_id,
                    select_difficulty=select_difficulty,
                ),
            )
            return 1


"""
def wait_room(token: str, room_id: int) -> list: # [status, [room_user_list]]
"""


def start_room(token: str, room_id: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE `room` SET `start`=1 WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
