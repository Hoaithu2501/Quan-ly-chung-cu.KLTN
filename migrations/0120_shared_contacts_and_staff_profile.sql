-- One person may hold several accounts (one per apartment), so email is no longer unique.
-- SQLite cannot drop a column constraint, hence the rebuild. No table references users by foreign key.
-- Staff have no resident record, so their name and ID number are kept on the account.
CREATE TABLE users_rebuilt (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    role            TEXT NOT NULL CHECK (role IN ('admin','resident','technician')),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','locked')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lock_reason     TEXT,
    token_version   INTEGER NOT NULL DEFAULT 0,
    full_name       TEXT,
    id_card         TEXT
);
INSERT INTO users_rebuilt (user_id,username,password_hash,email,phone,role,status,created_at,lock_reason,token_version)
SELECT user_id,username,password_hash,email,phone,role,status,created_at,lock_reason,token_version FROM users;
DROP TABLE users;
ALTER TABLE users_rebuilt RENAME TO users;

UPDATE users SET full_name=(SELECT t.full_name FROM technicians t WHERE t.user_id=users.user_id ORDER BY t.technician_id LIMIT 1)
WHERE role='technician';
