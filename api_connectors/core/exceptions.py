# api_connectors/core/exceptions.py
class APIError(Exception):
    """Erreur lors de l'appel d'une API externe"""
    pass


class NetworkOrServerError(APIError):
    """Erreur de connexion ou code de statut non géré (4xx, 5xx)."""
    pass