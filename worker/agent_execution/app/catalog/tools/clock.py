from datetime import datetime, timezone
"""Un Protocol (module typing) décrit une forme : « tout objet qui a une méthode now() renvoyant un datetime ». C'est un contrat, sans code derrière."""
from typing import Protocol


class Clock(Protocol):
    """Source de « maintenant » injectée dans les tools : toujours un datetime avec fuseau."""
    def now(self) -> datetime: ...  
    """Le ... dans le corps de now signifie « pas d'implémentation ici », car c'est seulement la signature."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
    

class FixedClock:
    def __init__(self, instant: datetime):
        if instant.tzinfo is None:
            raise ValueError("FixedClock exige un datetime avec fuseau")
        self._instant = instant

    def now(self) -> datetime:
        return self._instant