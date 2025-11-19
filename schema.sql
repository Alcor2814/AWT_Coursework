DROP TABLE if EXISTS users;
DROP TABLE if EXISTS collections;

CREATE TABLE users (
	UserEmail text,
	UserName text,
	EncryptedPassword text
);

CREATE TABLE collections (
	UserEmail text,
	ComicJson text,
	ComicReview text
);