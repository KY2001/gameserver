from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)
user_tokens = []
live_ids = [1000, 1001, 1002, 1003, 1004, 1500, 1501]
room_ids = []


def _create_users():  # ユーザー0, 1, ... 99を作成
    for i in range(100):
        response = client.post(
            "/user/create",
            json={"user_name": f"{i}", "leader_card_id": 1000 + (i % 3)},
        )
        user_tokens.append(response.json()["user_token"])


_create_users()


def _auth_header(i=0):
    token = user_tokens[i]
    return {"Authorization": f"bearer {token}"}


def test_room_2():
    for i in range(len(live_ids)):  # 全パターンの部屋の作成
        for j in range(2):
            response = client.post(
                "/room/create",
                headers=_auth_header(len(live_ids) * i + j),
                json={"live_id": live_ids[i], "select_difficulty": j + 1},
            )
            assert response.status_code == 200
            room_id = response.json()["room_id"]
            room_ids.append(room_id)
            # print(f"room/create {room_id=}")

    response = client.post("/room/list", json={"live_id": 0})  # 全部屋検索(ワイルドカード)
    assert response.status_code == 200
    # print("room/list response:", response.json())

    for live_id in live_ids:
        response = client.post("/room/list", json={"live_id": live_id})  # 各部屋の検索
        assert response.status_code == 200
        # print("room/list response:", response.json())

    for i in range(50, 53):  # 50 ～ 52が0が立てた部屋に入る
        response = client.post(
            "/room/join",
            headers=_auth_header(i),
            json={"room_id": room_ids[0], "select_difficulty": 1},
        )
        assert response.status_code == 200
        assert response.json()["join_room_result"] == 1  # 入場OK
        # print("room/join response:", response.json())

    response = client.post(  # 53が0が立てた部屋に入ろうとする → 満員
        "/room/join",
        headers=_auth_header(53),
        json={"room_id": room_ids[0], "select_difficulty": 1},
    )
    assert response.status_code == 200
    assert response.json()["join_room_result"] == 2  # 満員
    # print("room/join response:", response.json())

    response = client.post(  # 1が立てた部屋から抜ける
        "/room/leave", headers=_auth_header(1), json={"room_id": room_ids[1]}
    )
    assert response.status_code == 200

    response = client.post(  # 53が1が立てた部屋(解散済み)に入ろうとする → 解散済み
        "/room/join",
        headers=_auth_header(1),
        json={"room_id": room_ids[1], "select_difficulty": 1},
    )
    assert response.status_code == 200
    assert response.json()["join_room_result"] == 3  # 解散済み

    for _ in range(100):  # waitをルーム0の各参加者から100回送る
        for participant in [0, 50, 51, 52]:
            response = client.post(
                "/room/wait",
                headers=_auth_header(participant),
                json={"room_id": room_ids[0]},
            )
            assert response.status_code == 200
            # print("room/wait response:", response.json())

    response = client.post(  # 0(ホスト)が部屋0から抜ける → ホスト交代
        "/room/leave", headers=_auth_header(0), json={"room_id": room_ids[0]}
    )
    assert response.status_code == 200

    response = client.post(  # ホストが0から50, 51, 52のうちの誰に変わったかを取得
        "/room/wait", headers=_auth_header(50), json={"room_id": room_ids[0]}
    )
    assert response.status_code == 200
    res = response.json()["room_user_list"]
    host = -1
    for user in res:
        if user["is_host"]:
            host = int(user["name"])
    assert host != -1

    response = client.post(  # ホストがゲームをスタート
        "/room/start", headers=_auth_header(host), json={"room_id": room_ids[0]}
    )
    assert response.status_code == 200
    # print("room/wait response:", response.json())

    for user in [50, 51, 52]:  # 結果を投げる
        response = client.post(
            "/room/end",
            headers=_auth_header(user),
            json={
                "room_id": room_ids[0],
                "score": 1234,
                "judge_count_list": [4, 3, 2, 1, 3],
            },
        )
        assert response.status_code == 200
        # print("room/end response:", response.json())
        if user == 51:  # 全員揃っていない待機中は[]が返却される
            response = client.post(
                "/room/result",
                headers=_auth_header(user),
                json={"room_id": room_ids[0]},
            )
            assert response.status_code == 200
            assert response.json()["result_user_list"] == []
            # print("room/end response:", response.json())

    for user in [50, 51, 52]:  # 結果を取得
        response = client.post(
            "/room/result",
            headers=_auth_header(),
            json={"room_id": room_ids[0]},
        )
        assert response.status_code == 200
        # print("room/end response:", response.json())
