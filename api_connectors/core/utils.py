from datetime import datetime, timezone, timedelta

# --- Fonctions utilitaires de mapping et conversion ---

def convert_unix_to_localtime(timestamp:int, timezone_offset:int) -> str:
    if timestamp is None: return ""
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    dt_local = dt_utc + timedelta(seconds=timezone_offset)
    return dt_local.strftime("%H:%M:%S")