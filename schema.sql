DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT, -- user id
  `name` varchar(255) DEFAULT NULL, -- name
  `token` varchar(255) DEFAULT NULL, -- user token
  `leader_card_id` int DEFAULT NULL, -- 選んだアバター
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
    `room_id` bigint NOT NULL AUTO_INCREMENT, -- room id
    `live_id` bigint NOT NULL,
    `start` int NOT NULL DEFAULT 0, -- ゲームが開始したかどうか
    PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `id` bigint NOT NULL AUTO_INCREMENT, -- user id
  `room_id` bigint NOT NULL,
  `select_difficulty` int NOT NULL,
  `is_host` int NOT NULL DEFAULT 0, -- ホストかどうか
  UNIQUE KEY `id` (`id`)
);