import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine

# from .api import Live_Difficulty


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


class LiveDifficulty(IntEnum):
    normal = 1
    hard = 2


class JoinRoomResult(IntEnum):
    OK = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(IntEnum):
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
    select_difficulty: LiveDifficulty
    is_me: bool
    is_host: bool


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list
    score: int


def create_room(token: str, live_id: int, select_difficulty: int) -> int:
    user_id = get_user_by_token(token).id  # ホストのユーザidを取得
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


def get_room_info(live_id: int) -> list[RoomInfo]:
    with engine.begin() as conn:
        if live_id == 0:  # live_id = 0のとき全てのルームを対象とする
            result = conn.execute(text("SELECT `room_id`, `start` FROM `room`"))
        else:
            result = conn.execute(
                text("SELECT `room_id`, `start` FROM `room` WHERE `live_id`=:live_id"),
                dict(live_id=live_id),
            )
        rows = result.all()
        room_info_list = []
        for row in rows:
            if row.start:  # 既にスタート済みのルームは除く
                continue
            result = conn.execute(
                text("SELECT COUNT(`id`) FROM `room_member` WHERE `room_id`=:room_id"),
                dict(room_id=row.room_id),
            )
            joined_user_count = result.one()["COUNT(`id`)"]
            if joined_user_count == max_user_count:  # 満員のルームを除く
                continue
            room_info_list.append(
                RoomInfo(
                    room_id=row.room_id,
                    live_id=live_id,
                    joined_user_count=joined_user_count,
                    max_user_count=max_user_count,
                )
            )
        return room_info_list


def join_room(token: str, room_id: int, select_difficulty: int) -> int:
    user_id = get_user_by_token(token).id  # joinするユーザのidを取得
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


def wait_room(token: str, room_id: int) -> list[WaitRoomStatus, list[RoomUser]]:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT `start` FROM `room` WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        try:  # 結果が帰ってくる=部屋が存在する場合
            row = result.one()
            status = WaitRoomStatus(row.start + 1)
            result = conn.execute(
                text(
                    "SELECT `id`, `select_difficulty`, `is_host` FROM `room_member` WHERE `room_id`=:room_id"
                ),
                dict(room_id=room_id),
            )
            list_room_use = []
            for member in result.all():
                result_user = conn.execute(
                    text(
                        "SELECT `name`, `leader_card_id`, `token` FROM `user` WHERE `id`=:id"
                    ),
                    dict(id=member.id),
                )
                row = result_user.one()
                list_room_use.append(
                    RoomUser(
                        user_id=member.id,
                        name=row.name,
                        leader_card_id=row.leader_card_id,
                        select_difficulty=LiveDifficulty(member.select_difficulty),
                        is_host=True if member.is_host else False,
                        is_me=True if row.token == token else False,
                    )
                )
            return [status, list_room_use]
        except NoResultFound:  # 部屋が解散した場合
            return [3, []]


def start_room(token: str, room_id: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE `room` SET `start`=1 WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )


def end_room(token: str, room_id: int, judge_count_list: list[int], score: int) -> None:
    user_id = get_user_by_token(token).id  # endするユーザのidを取得
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE `room_member` SET `score`=:score, `perfect`=:perfect, `great`=:great, `good`=:good, `bad`=:bad, `miss`=:miss WHERE `id`=:user_id"
            ),
            dict(
                score=score,
                user_id=user_id,
                perfect=judge_count_list[0],
                great=judge_count_list[1],
                good=judge_count_list[2],
                bad=judge_count_list[3],
                miss=judge_count_list[4],
            ),
        )


def leave_room(token: str, room_id: int) -> None:
    user_id = get_user_by_token(token).id  # leaveするユーザのidを取得
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT `id`, `is_host` FROM `room_member` WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        rows = result.all()
        if len(rows) == 1:  # leaveするユーザーしか残っていない -> ルームを解散
            result = conn.execute(  # ルームを削除
                text("DELETE FROM `room` WHERE `room_id`=:room_id"),
                dict(room_id=room_id),
            )
        else:
            for member in rows:
                if (
                    member.id == user_id and member.is_host
                ):  # leaveするユーザーがホストの場合 -> ホストを譲る
                    for member2 in rows:
                        if member2.id != user_id:
                            result = conn.execute(
                                text(
                                    "UPDATE `room_member` SET `is_host`=1 WHERE `id`=:id"
                                ),
                                dict(id=member2.id),
                            )
                            break
                    break
        result = conn.execute(  # ユーザーをルームから削除
            text("DELETE FROM `room_member` WHERE `id`=:id"),
            dict(id=user_id),
        )


def get_result(token: str, room_id: int) -> list[ResultUser]:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT `id`, `score`, `perfect`, `great`, `good`, `bad`, `miss` FROM `room_member` WHERE `room_id`=:room_id"
            ),
            dict(room_id=room_id),
        )
        rows = result.all()
        for member in rows:  # 終わっていないメンバーが居る場合は空のリストを返す
            if member.score is None:
                return []
        list_result_user = []
        for member in rows:
            judge_count_list = [
                member.perfect,
                member.great,
                member.good,
                member.bad,
                member.miss,
            ]
            list_result_user.append(
                ResultUser(
                    user_id=member.id,
                    judge_count_list=judge_count_list,
                    score=member.score,
                )
            )
        leave_room(token, room_id)  # 結果を受け取ったら部屋から退出
        return list_result_user
