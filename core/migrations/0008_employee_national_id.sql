-- Employee national ID (الرقم القومي), printed on handover and return receipts.
-- Personal data: only users who manage employees or assignments see it in full; everyone else sees the last 4 digits.

ALTER TABLE employees ADD COLUMN national_id TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX idx_employees_national_id ON employees(national_id) WHERE national_id <> '';
