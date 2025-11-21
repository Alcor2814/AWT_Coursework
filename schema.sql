DROP TABLE if EXISTS users;
DROP TABLE if EXISTS collections;
DROP TABLE if EXISTS comics;

CREATE TABLE users (
	UserEmail TEXT,
	UserName TEXT,
	EncryptedPassword TEXT
);

CREATE TABLE collections (
	UserEmail TEXT,
	ComicId INTEGER,
	ComicReview TEXT,
	DisplayReview TEXT
);

CREATE TABLE comics (
	id INTEGER,
	name TEXT,
	store_date TEXT,
	image TEXT,
	issue_number INTEGER,
	description TEXT,
	volume TEXT
);