from datetime import datetime, timedelta

# --- Fonctions utilitaires de mapping et conversion ---

def convert_unix_to_localtime(timestamp: int, timezone_offset: int) -> str:
    """
    Convertit un timestamp UNIX (UTC) en une chaîne de date/heure locale
    en appliquant le décalage du fuseau horaire.
    Retourne l'heure formatée 'HH:MM:SS'.
    """
    if timestamp is None:
        return ""

    # 1. Créer l'objet datetime UTC
    dt_utc = datetime.fromtimestamp(timestamp)

    # 2. Créer l'objet timedelta pour le décalage
    offset_delta = timedelta(seconds=timezone_offset)

    # 3. Appliquer le décalage pour obtenir l'heure locale
    dt_local = dt_utc + offset_delta

    # 4. Formater l'heure
    return dt_local.strftime('%H:%M:%S')