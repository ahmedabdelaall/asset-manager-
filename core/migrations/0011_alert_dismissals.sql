-- Alerts a user has dismissed from the bell. Each key names one alert and the date it is about
-- (for example "overdue:<asset id>:<expected return>"), so the alert comes back by itself when that changes.
-- Dismissing is personal: other users still see the alert.

CREATE TABLE alert_dismissals (
    user_id    INTEGER NOT NULL REFERENCES users(id),
    alert_key  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, alert_key)
);
