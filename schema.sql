DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT, -- user id
  `name` varchar(255) DEFAULT NULL, -- name
  `token` varchar(255) DEFAULT NULL, -- user token
  `leader_card_id` int DEFAULT NULL, -- avatar one chose
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
    `room_id` bigint NOT NULL AUTO_INCREMENT, -- room id
    `live_id` bigint NOT NULL,
    PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `id` bigint NOT NULL AUTO_INCREMENT, -- user id
  `room_id` bigint NOT NULL,
  `select_difficulty` int NOT NULL,
  `is_host` int NOT NULL DEFAULT 0, -- is_host?
  PRIMARY KEY (`room_id`),
  UNIQUE KEY `id` (`id`)
);