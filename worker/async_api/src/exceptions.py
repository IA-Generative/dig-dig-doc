"""Erreurs rendues au consommateur : `mic_worker` publie `str(erreur)` dans le message d'échec."""


class AnalysisError(Exception):
    """Base : le message est destiné au consommateur, pas au journal."""


class InvalidRequestError(AnalysisError):
    """Message d'entrée non conforme au contrat."""


class FileTooLargeError(AnalysisError):
    """Un fichier (ou leur total) dépasse la limite mémoire du worker."""


class RunFailedError(AnalysisError):
    """Le run dig-dig-doc s'est terminé en `échec` ou `arrêté`."""


class RunTimeoutError(AnalysisError):
    """Le run n'a pas atteint un état terminal dans le délai imparti."""
