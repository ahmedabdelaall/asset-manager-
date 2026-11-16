# -*- coding: utf-8 -*-
"""Automatic daily database backup + retention."""
import time
import logging
import threading

log = logging.getLogger("am.backup")


class BackupScheduler(threading.Thread):
    def __init__(self, db, inst):
        super().__init__(daemon=True)
        self.db, self.inst = db, inst
        self._halt = threading.Event()
        self._last_day = None

    def stop(self):
        self._halt.set()

    def run(self):
        while not self._halt.wait(60):
            hour = int(self.inst.config["auto_backup_hour"])
            if hour < 0:
                continue
            lt = time.localtime()
            if lt.tm_hour >= hour and self._last_day != lt.tm_yday:
                try:
                    self.db.backup("auto")
                    self.db.prune_backups(int(self.inst.config["backup_keep"]))
                    self._last_day = lt.tm_yday
                    log.info("Automatic backup done")
                except Exception as e:
                    log.error("Automatic backup failed: %s", e)
