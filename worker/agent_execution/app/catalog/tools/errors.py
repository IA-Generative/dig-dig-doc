class ToolError(Exception):
    """Exception est la classe de base Python pour toutes les erreurs 'normales'"""
    """Rôle de la class : Erreur d'un tool, au format que l'agent comprend."""

    """le __init__ ici permet d'appeler automatiquement cette fonction à chaque fois que l'on créé un objet de cette class. Il sert à donner à l'objet son objet son état de départ."""
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {"ok": False, "error": {"code": self.code, "message": self.message, "details": self.details}}


def ok(**valeurs) -> dict:
    """**<nom_de_paramètre>,dans cette fonction, veut dire 'accepte n'importe quel nombre de paramètres nommés, et range-les dans un dictionnaire appelé valeurs'. Le nom 'valeurs' est libre."""

    """Rôle de la classe: réponse de succès --> ok: true + le résultat."""

    """le ** dans le return déplie un dictionnaire dans un autre"""
    """On ne peut appeler ok qu'avec des paramètres nommés (ok(a=1)). ok(1) provoque une erreur. C'est voulu, car chaque valeur du résultat doit avoir un nom."""
    return {"ok": True, **valeurs}