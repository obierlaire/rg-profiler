-- Initialize PostgreSQL database for RG Profiler

-- Create World table
CREATE TABLE IF NOT EXISTS world (
  id integer NOT NULL,
  randomnumber integer NOT NULL,
  CONSTRAINT world_pkey PRIMARY KEY (id)
);

-- Create Fortune table for template tests
CREATE TABLE IF NOT EXISTS fortune (
  id integer NOT NULL,
  message text NOT NULL,
  CONSTRAINT fortune_pkey PRIMARY KEY (id)
);

-- Create users table for session tests
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) NOT NULL,
  password VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create sessions table 
CREATE TABLE IF NOT EXISTS sessions (
  id VARCHAR(100) PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  data JSONB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL
);

-- Create data table for serialization tests
CREATE TABLE IF NOT EXISTS complex_data (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  data JSONB NOT NULL,
  tags TEXT[] NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Populate World table with sample data
INSERT INTO world (id, randomnumber)
SELECT x, floor(random() * 10000 + 1)::integer
FROM generate_series(1, 10000) AS x;

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
('Item 1', '{"properties": {"color": "red", "size": "large"}, "metrics": {"views": 123, "likes": 42}, "nested": {"level1": {"level2": {"value": 42}}}}', ARRAY['tag1', 'tag2', 'red']),
('Item 2', '{"properties": {"color": "blue", "size": "medium"}, "metrics": {"views": 56, "likes": 8}, "nested": {"level1": {"level2": {"value": 18}}}}', ARRAY['tag3', 'tag2', 'blue']),
('Item 3', '{"properties": {"color": "green", "size": "small"}, "metrics": {"views": 987, "likes": 241}, "nested": {"level1": {"level2": {"value": 99}}}}', ARRAY['tag1', 'tag4', 'green']);
