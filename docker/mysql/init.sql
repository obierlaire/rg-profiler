-- Initialize MySQL database for RG Profiler

-- Use the benchmark database
USE hello_world;

-- Create World table
CREATE TABLE IF NOT EXISTS world (
  id int NOT NULL,
  randomnumber int NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

-- Create Fortune table for template tests
CREATE TABLE IF NOT EXISTS fortune (
  id int NOT NULL,
  message varchar(2048) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

-- Create users table for session tests
CREATE TABLE IF NOT EXISTS users (
  id int NOT NULL AUTO_INCREMENT,
  username varchar(50) NOT NULL,
  password varchar(100) NOT NULL,
  email varchar(100) NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

-- Create sessions table 
CREATE TABLE IF NOT EXISTS sessions (
  id varchar(100) NOT NULL,
  user_id int,
  data JSON NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at timestamp NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- Create data table for serialization tests
CREATE TABLE IF NOT EXISTS complex_data (
  id int NOT NULL AUTO_INCREMENT,
  name varchar(100) NOT NULL,
  data JSON NOT NULL,
  tags JSON NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

-- Populate World table with sample data
DELIMITER //
CREATE PROCEDURE populate_world()
BEGIN
  DECLARE i INT DEFAULT 1;
  WHILE i <= 10000 DO
    INSERT INTO world (id, randomnumber) VALUES (i, FLOOR(1 + RAND() * 10000));
    SET i = i + 1;
  END WHILE;
END //
DELIMITER ;

CALL populate_world();
DROP PROCEDURE populate_world;

-- Populate Fortune table with sample data
INSERT INTO fortune (id, message) VALUES (1, 'fortune: No such file or directory');
INSERT INTO fortune (id, message) VALUES (2, 'A computer scientist is someone who fixes things that aren''t broken.');
INSERT INTO fortune (id, message) VALUES (3, 'After enough decimal places, nobody gives a damn.');
INSERT INTO fortune (id, message) VALUES (4, 'A bad random number generator: 1, 1, 1, 1, 1, 4.33e+67, 1, 1, 1');
INSERT INTO fortune (id, message) VALUES (5, 'A computer program does what you tell it to do, not what you want it to do.');
INSERT INTO fortune (id, message) VALUES (6, 'Emacs is a nice operating system, but I prefer UNIX. — Tom Christaensen');
INSERT INTO fortune (id, message) VALUES (7, 'Any program that runs right is obsolete.');
INSERT INTO fortune (id, message) VALUES (8, 'A list is only as strong as its weakest link. — Donald Knuth');
INSERT INTO fortune (id, message) VALUES (9, 'Feature: A bug with seniority.');
INSERT INTO fortune (id, message) VALUES (10, 'Computers make very fast, very accurate mistakes.');
INSERT INTO fortune (id, message) VALUES (11, '<script>alert("This should not be displayed in a browser alert box.");</script>');
INSERT INTO fortune (id, message) VALUES (12, 'フレームワークのベンチマーク');

-- Populate users table with sample data
INSERT INTO users (username, password, email) 
VALUES ('testuser', 'password123', 'test@example.com'),
       ('john', 'securepass', 'john@example.com'),
       ('alice', 'pass123', 'alice@example.com');

-- Populate complex data for serialization tests
INSERT INTO complex_data (name, data, tags) VALUES 
('Item 1', '{"properties": {"color": "red", "size": "large"}, "metrics": {"views": 123, "likes": 42}, "nested": {"level1": {"level2": {"value": 42}}}}', '["tag1", "tag2", "red"]'),
('Item 2', '{"properties": {"color": "blue", "size": "medium"}, "metrics": {"views": 56, "likes": 8}, "nested": {"level1": {"level2": {"value": 18}}}}', '["tag3", "tag2", "blue"]'),
('Item 3', '{"properties": {"color": "green", "size": "small"}, "metrics": {"views": 987, "likes": 241}, "nested": {"level1": {"level2": {"value": 99}}}}', '["tag1", "tag4", "green"]');
