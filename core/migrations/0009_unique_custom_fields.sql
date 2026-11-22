-- A category field can be marked "unique": no two assets of that category may have the same value
-- (e.g. a mobile line's phone number, or a phone's IMEI). Checked in core/inventory.py.

ALTER TABLE category_fields ADD COLUMN unique_value INTEGER NOT NULL DEFAULT 0;
