from __future__ import annotations

from app.config import settings
from app.storage import Database


db = Database(settings.database_path)
db.reset_music_data()
print("NOMAD music database reset.")
print(db.stats())
db.close()
