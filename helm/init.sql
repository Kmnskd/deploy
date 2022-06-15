CREATE USER 'user_center'@'%' IDENTIFIED BY 'user_center@>*123';
GRANT ALL ON user_center_db.* TO 'user_center'@'%';

DROP DATABASE IF EXISTS `user_center_db`;
CREATE DATABASE IF NOT EXISTS `user_center_db`  DEFAULT CHARACTER SET utf8;



CREATE USER 'client_integration'@'%' IDENTIFIED BY 'client_integration@>*123';
GRANT ALL ON client_integration_db.* TO 'client_integration'@'%';

DROP DATABASE IF EXISTS `client_integration_db`;
CREATE DATABASE IF NOT EXISTS `client_integration_db`  DEFAULT CHARACTER SET utf8;



CREATE USER 'baseline_cloud'@'%' IDENTIFIED BY 'baseline_cloud@>*123';
GRANT ALL ON baseline_cloud_db.* TO 'baseline_cloud'@'%';

DROP DATABASE IF EXISTS `baseline_cloud_db`;
CREATE DATABASE IF NOT EXISTS `baseline_cloud_db`  DEFAULT CHARACTER SET utf8;