-- Удаляем старую базу данных, если она существует
DROP DATABASE IF EXISTS `test_serp`;

-- --------------------------------------------------------
-- Хост:                         127.0.0.1
-- Версия сервера:               8.0.40 - MySQL Community Server - GPL
-- Операционная система:         Win64
-- HeidiSQL Версия:              12.8.0.6908
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Дамп структуры базы данных test_serp
CREATE DATABASE IF NOT EXISTS `test_serp` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `test_serp`;

-- Дамп структуры для таблица test_serp.parsing_results
CREATE TABLE IF NOT EXISTS `parsing_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int DEFAULT NULL,
  `url` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `processed` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `parsing_results_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.parsing_results: ~8 rows (приблизительно)
DELETE FROM `parsing_results`;
INSERT INTO `parsing_results` (`id`, `query`, `position`, `url`, `processed`, `created_at`, `user_id`) VALUES
	(4, 'мужская шуба из каракуля', 2, 'https://moscow.sobol-mex.ru/meha-dlya-muzhchin/muzhskie-kurtki-iz-mexa', 'Yes', '2025-11-01 21:06:43', NULL),
	(5, 'мужская каракулевая шуба', 3, 'https://moscow.sobol-mex.ru/meha-dlya-muzhchin/muzhskie-kurtki-iz-mexa', 'Yes', '2025-11-01 21:06:43', NULL),
	(6, 'sobol-mex.ru', 1, 'https://sobol-mex.ru/', 'Yes', '2025-11-01 23:58:46', NULL),
	(7, 'sobol-mex.ru', 1, 'https://sobol-mex.ru/', 'Yes', '2025-11-02 00:24:58', NULL),
	(8, '333', NULL, '-', 'Yes', '2025-11-02 16:02:40', NULL),
	(9, '333', NULL, '-', 'Yes', '2025-11-02 16:02:40', NULL),
	(10, 'Тест', NULL, '-', 'Yes', '2025-11-02 16:25:52', NULL),
	(11, 'Тест 1', NULL, '-', 'Yes', '2025-11-02 16:25:52', NULL);

-- Дамп структуры для таблица test_serp.parsing_sessions
CREATE TABLE IF NOT EXISTS `parsing_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `domain` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `engine` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('running','completed','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `parsing_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.parsing_sessions: ~4 rows (приблизительно)
DELETE FROM `parsing_sessions`;
INSERT INTO `parsing_sessions` (`id`, `session_id`, `domain`, `engine`, `status`, `created_at`, `completed_at`, `user_id`) VALUES
	(4, 'session_20251102_010626_9aa0a643', 'https://sobol-mex.ru/', 'yandex', 'completed', '2025-11-01 21:06:26', '2025-11-01 21:06:43', 1),
	(8, 'session_20251102_200222_8ae11cb8', 'https://sobol-mex.ru/', 'yandex', 'completed', '2025-11-02 16:02:22', '2025-11-02 16:02:41', 1),
	(9, 'session_20251102_202537_e84755a7', 'https://sobol-mex.ru/', 'yandex', 'completed', '2025-11-02 16:25:37', '2025-11-02 16:25:52', 1);

-- Дамп структуры для таблица test_serp.search_results
CREATE TABLE IF NOT EXISTS `search_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `url` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `search_results_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `search_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.search_results: ~0 rows (приблизительно)
DELETE FROM `search_results`;

-- Дамп структуры для таблица test_serp.search_tasks
CREATE TABLE IF NOT EXISTS `search_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int DEFAULT NULL,
  `search_engine` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `region` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `device` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `depth` int DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `search_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.search_tasks: ~0 rows (приблизительно)
DELETE FROM `search_tasks`;

-- Дамп структуры для таблица test_serp.search_task_results
CREATE TABLE IF NOT EXISTS `search_task_results` (
  `search_task_id` int NOT NULL,
  `search_result_id` int NOT NULL,
  PRIMARY KEY (`search_task_id`,`search_result_id`),
  KEY `search_result_id` (`search_result_id`),
  CONSTRAINT `search_task_results_ibfk_1` FOREIGN KEY (`search_task_id`) REFERENCES `search_tasks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `search_task_results_ibfk_2` FOREIGN KEY (`search_result_id`) REFERENCES `search_results` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.search_task_results: ~0 rows (приблизительно)
DELETE FROM `search_task_results`;

-- Дамп структуры для таблица test_serp.session_results
CREATE TABLE IF NOT EXISTS `session_results` (
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_id` int NOT NULL,
  PRIMARY KEY (`session_id`,`result_id`),
  KEY `result_id` (`result_id`),
  CONSTRAINT `session_results_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `parsing_sessions` (`session_id`) ON DELETE CASCADE,
  CONSTRAINT `session_results_ibfk_2` FOREIGN KEY (`result_id`) REFERENCES `parsing_results` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.session_results: ~0 rows (приблизительно)
DELETE FROM `session_results`;
INSERT INTO `session_results` (`session_id`, `result_id`) VALUES
	('session_20251102_010626_9aa0a643', 4),
	('session_20251102_010626_9aa0a643', 5),
	('session_20251102_200222_8ae11cb8', 8),
	('session_20251102_200222_8ae11cb8', 9),
	('session_20251102_202537_e84755a7', 10),
	('session_20251102_202537_e84755a7', 11);

-- Дамп структуры для таблица test_serp.top_sites_queries
CREATE TABLE IF NOT EXISTS `top_sites_queries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `query_text` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('pending','running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `top_sites_queries_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `top_sites_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.top_sites_queries: ~8 rows (приблизительно)
DELETE FROM `top_sites_queries`;
INSERT INTO `top_sites_queries` (`id`, `task_id`, `query_text`, `status`) VALUES
	(35, 32, 'мужская шуба из бобра', 'completed'),
	(36, 32, 'купить мужскую шубу из бобра', 'completed'),
	(37, 32, 'мужская бобровая шуба', 'completed'),
	(38, 32, 'бобровая мужская шуба купить', 'completed'),
	(39, 33, 'мужская шуба из бобра', 'completed'),
	(40, 33, 'купить мужскую шубу из бобра', 'completed'),
	(41, 33, 'мужская бобровая шуба', 'completed'),
	(42, 33, 'бобровая мужская шуба купить', 'completed');

-- Дамп структуры для таблица test_serp.top_sites_results
CREATE TABLE IF NOT EXISTS `top_sites_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query_id` int NOT NULL,
  `url` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `query_id` (`query_id`),
  CONSTRAINT `top_sites_results_ibfk_1` FOREIGN KEY (`query_id`) REFERENCES `top_sites_queries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.top_sites_results: ~98 rows (приблизительно)
DELETE FROM `top_sites_results`;
INSERT INTO `top_sites_results` (`id`, `query_id`, `url`, `position`) VALUES
	(481, 35, 'https://www.avito.ru/all?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 1),
	(482, 35, 'https://www.avito.ru/moskva/odezhda_obuv_aksessuary/muzhskaya_odezhda-ASgBAgICAUTeAtgL?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0', 2),
	(483, 35, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 3),
	(484, 35, 'https://yandex.ru/images/search?text=%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F+%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0', 4),
	(485, 35, 'https://www.ozon.ru/product/shuba-mehovaya-fabrika-sobol-1865283467/', 5),
	(486, 35, 'https://www.livemaster.ru/popular/14129-muzhskaya-shuba-iz-bobra', 6),
	(487, 35, 'https://www.wildberries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 7),
	(488, 35, 'https://www.mosmexa.ru/man/mshubii/product=31465.html', 8),
	(489, 35, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 9),
	(490, 35, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 10),
	(491, 35, 'https://www.avito.ru/moskva?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 11),
	(492, 35, 'https://moscow.sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 12),
	(493, 35, 'https://www.ozon.ru/product/shuba-mehovaya-fabrika-sobol-1949294441/', 13),
	(494, 35, 'https://www.livemaster.ru/item/30313287-odezhda-shuba-muzhskaya-iz-bobra-strizhennogo-krashennogo-tsv', 14),
	(495, 35, 'https://www.ozon.ru/category/shuba-bobr/', 15),
	(496, 35, 'https://www.wildberries.ru/catalog/193751467/detail.aspx', 16),
	(497, 35, 'https://melita.ru/collection-category-13.html', 17),
	(498, 36, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 1),
	(499, 36, 'https://www.avito.ru/moskva/odezhda_obuv_aksessuary/muzhskaya_odezhda-ASgBAgICAUTeAtgL?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0', 2),
	(500, 36, 'https://www.mosmexa.ru/man/mshubii/product=31465.html', 3),
	(501, 36, 'https://www.ozon.ru/category/shuba-bobr/', 4),
	(502, 36, 'https://www.livemaster.ru/popular/14129-muzhskaya-shuba-iz-bobra', 5),
	(503, 36, 'https://www.wildberries.ru/catalog/193751467/detail.aspx', 6),
	(504, 36, 'https://lilia54.ru/products/category/2615925', 7),
	(505, 36, 'http://xn--j1amisx4a.xn--p1ai/catalog/muzhskie', 8),
	(506, 36, 'https://www.furprice.ru/catalog/muzhskaya_verkhnyaya_odezhda/muzhskie_shuby/2009/', 9),
	(507, 36, 'https://www.spbmeh.ru/catalog/karakulcha_bobyer/', 10),
	(508, 36, 'https://www.avito.ru/moskva?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 11),
	(509, 36, 'https://www.wildberries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 12),
	(510, 36, 'https://yandex.ru/images/search?text=%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D1%83%D1%8E+%D1%88%D1%83%D0%B1%D1%83+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0', 13),
	(511, 36, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 14),
	(512, 36, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 15),
	(513, 36, 'https://www.avito.ru/all?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 16),
	(514, 37, 'https://www.avito.ru/all?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 1),
	(515, 37, 'https://www.avito.ru/moskva/odezhda_obuv_aksessuary/muzhskaya_odezhda-ASgBAgICAUTeAtgL?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0', 2),
	(516, 37, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 3),
	(517, 37, 'https://yandex.ru/images/search?text=%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F+%D0%B1%D0%BE%D0%B1%D1%80%D0%BE%D0%B2%D0%B0%D1%8F+%D1%88%D1%83%D0%B1%D0%B0', 4),
	(518, 37, 'https://www.wildberries.ru/catalog/193751467/detail.aspx', 5),
	(519, 37, 'https://www.livemaster.ru/item/30313287-odezhda-shuba-muzhskaya-iz-bobra-strizhennogo-krashennogo-tsv', 6),
	(520, 37, 'https://www.ozon.ru/category/shuba-bobr/', 7),
	(521, 37, 'https://www.mosmexa.ru/man/mshubii/product=31465.html', 8),
	(522, 37, 'https://market.yandex.ru/category/shuby-iz-bobra-muzhskiye', 9),
	(523, 37, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 10),
	(524, 37, 'https://www.wildberries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 11),
	(525, 37, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 12),
	(526, 37, 'https://melita.ru/collection-category-13.html', 13),
	(527, 38, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 1),
	(528, 38, 'https://www.avito.ru/all?q=%D1%88%D1%83%D0%B1%D0%B0+%D0%B8%D0%B7+%D0%B1%D0%BE%D0%B1%D1%80%D0%B0+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F', 2),
	(529, 38, 'https://www.livemaster.ru/item/30313287-odezhda-shuba-muzhskaya-iz-bobra-strizhennogo-krashennogo-tsv', 3),
	(530, 38, 'https://www.mosmexa.ru/man/mshubii/product=31465.html', 4),
	(531, 38, 'https://www.wildberries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 5),
	(532, 38, 'https://www.ozon.ru/category/shuba-bobr/', 6),
	(533, 38, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 7),
	(534, 38, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 8),
	(535, 38, 'https://market.yandex.ru/category/shuby-iz-bobra-muzhskiye', 9),
	(536, 38, 'https://yandex.ru/images/search?text=%D0%B1%D0%BE%D0%B1%D1%80%D0%BE%D0%B2%D0%B0%D1%8F+%D0%BC%D1%83%D0%B6%D1%81%D0%BA%D0%B0%D1%8F+%D1%88%D1%83%D0%B1%D0%B0+%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C', 10),
	(537, 38, 'https://www.livemaster.ru/popular/14129-muzhskaya-shuba-iz-bobra', 11),
	(538, 38, 'https://melita.ru/collection-category-13.html', 12),
	(539, 39, 'https://www.Avito.ru/moskva?q=шуба из бобра мужская', 1),
	(540, 39, 'https://www.Avito.ru/moskva/odezhda_obuv_aksessuary/muzhskaya_odezhda-ASgBAgICAUTeAtgL?q=шуба из бобра', 2),
	(541, 39, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 3),
	(542, 39, 'https://www.OZON.ru/product/shuba-mehovaya-fabrika-sobol-1865283467/', 4),
	(543, 39, 'https://www.livemaster.ru/popular/14129-muzhskaya-shuba-iz-bobra', 5),
	(544, 39, 'https://www.MosMexa.ru/man/mshubii/product=31465.html', 6),
	(545, 39, 'https://www.WildBerries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 7),
	(546, 39, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 8),
	(547, 39, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 9),
	(548, 39, 'https://market.yandex.ru/category/shuby-iz-bobra-muzhskiye', 10),
	(549, 40, 'https://www.Avito.ru/moskva/odezhda_obuv_aksessuary/muzhskaya_odezhda-ASgBAgICAUTeAtgL?q=шуба из бобра', 1),
	(550, 40, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 2),
	(551, 40, 'https://www.MosMexa.ru/man/mshubii/product=31465.html', 3),
	(552, 40, 'https://www.livemaster.ru/popular/14129-muzhskaya-shuba-iz-bobra', 4),
	(553, 40, 'https://www.OZON.ru/category/shuba-bobr/', 5),
	(554, 40, 'https://www.WildBerries.ru/catalog/193751467/detail.aspx', 6),
	(555, 40, 'https://melita.ru/collection-category-13.html', 7),
	(556, 40, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 8),
	(557, 40, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 9),
	(558, 40, 'https://market.yandex.ru/category/shuby-iz-bobra-muzhskiye', 10),
	(559, 41, 'https://www.Avito.ru/all?q=шуба из бобра мужская', 1),
	(560, 41, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 2),
	(561, 41, 'https://www.OZON.ru/category/shuba-bobr/', 3),
	(562, 41, 'https://www.MosMexa.ru/man/mshubii/product=31465.html', 4),
	(563, 41, 'https://www.livemaster.ru/item/30313287-odezhda-shuba-muzhskaya-iz-bobra-strizhennogo-krashennogo-tsv', 5),
	(564, 41, 'https://arktur-22.ru/magazin/folder/shuby-muzhskie-iz-bobra', 6),
	(565, 41, 'https://melita.ru/collection-category-13.html', 7),
	(566, 41, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 8),
	(567, 41, 'https://AliExpress.ru/popular/мужская-шуба-из-стриженного-бобра', 9),
	(568, 41, 'https://www.edita-kmv.ru/catalog/muzhchinam/shuby107/shuby-iz-mekha-bolotnogo-bobra/', 10),
	(569, 42, 'https://www.Avito.ru/all?q=шуба из бобра мужская', 1),
	(570, 42, 'https://sobol-mex.ru/meha-dlya-muzhchin/russky-bobr/', 2),
	(571, 42, 'https://www.MosMexa.ru/man/mshubii/product=31465.html', 3),
	(572, 42, 'https://www.OZON.ru/category/shuba-bobr/', 4),
	(573, 42, 'https://www.livemaster.ru/item/30313287-odezhda-shuba-muzhskaya-iz-bobra-strizhennogo-krashennogo-tsv', 5),
	(574, 42, 'https://www.WildBerries.ru/catalog/tags/shuba-iz-bobra-naturalbnaja', 6),
	(575, 42, 'https://market.yandex.ru/category/shuby-iz-bobra-muzhskiye', 7),
	(576, 42, 'https://AliExpress.ru/popular/мужская-шуба-из-стриженного-бобра', 8),
	(577, 42, 'https://msk.ko-kirov.ru/muzhskie-shuby-iz-bobra', 9),
	(578, 42, 'https://melita.ru/collection-category-13.html', 10);

-- Дамп структуры для таблица test_serp.top_sites_tasks
CREATE TABLE IF NOT EXISTS `top_sites_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `search_engine` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `region` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `device` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `depth` int DEFAULT NULL,
  `status` enum('running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `top_sites_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.top_sites_tasks: ~2 rows (приблизительно)
DELETE FROM `top_sites_tasks`;
INSERT INTO `top_sites_tasks` (`id`, `user_id`, `search_engine`, `region`, `device`, `depth`, `status`, `created_at`, `completed_at`) VALUES
	(32, 1, 'yandex', 'RU', 'desktop', 10, 'completed', '2025-11-02 17:07:57', '2025-11-02 17:11:28'),
	(33, 1, 'yandex', 'RU', 'desktop', 10, 'completed', '2025-11-02 17:14:36', '2025-11-02 17:14:58');

-- Дамп структуры для таблица test_serp.users
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reset_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reset_token_expires` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Дамп данных таблицы test_serp.users: ~0 rows (приблизительно)
DELETE FROM `users`;
INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `reset_token`, `reset_token_expires`, `created_at`, `last_login`) VALUES
	(1, 'Serp', 'aa220380@gmail.com', 'scrypt:32768:8:1$068PO6azbrpy40Ry$f24c9a1e84a2e1cd03ad2376384adb78a938d141bd8ed4848f1bf5373f6ca2cbc862ab3681a2b26c9cef29c2d1d64106507a9a9c2631a0a854aa2fb419700c08', NULL, NULL, '2025-11-01 18:32:51', '2025-11-02 23:27:16');

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;