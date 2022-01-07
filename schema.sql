DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY, -- ユーザーID
  `name` varchar(255) DEFAULT NULL, -- ユーザー名
  `token` varchar(255) DEFAULT NULL UNIQUE KEY, -- ユーザートークン
  `leader_card_id` int DEFAULT NULL, -- 選んだアバター
  INDEX (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` bigint NOT NULL AUTO_INCREMENT PRIMARY KEY, -- ルームID
  `live_id` bigint NOT NULL, -- ライブID
  `start` int NOT NULL DEFAULT 0, -- ゲームが開始したかどうか
  INDEX (`room_id`)
);

DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `id` bigint NOT NULL AUTO_INCREMENT UNIQUE KEY, -- ユーザーID
  `room_id` bigint NOT NULL, -- ルームID
  `select_difficulty` int NOT NULL, -- 選択難易度
  `is_host` int NOT NULL DEFAULT 0, -- ホストかどうか
  `score` bigint, -- スコア
  `perfect` int, -- 各判定数(perfect)
  `great` int, -- 各判定数(great)
  `good` int, -- 各判定数(good)
  `bad` int, -- 各判定数(bad)
  `miss` int, -- 各判定数(miss)
  PRIMARY KEY (`room_id`, `id`)
);