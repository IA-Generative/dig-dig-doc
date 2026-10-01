from pydantic_settings import BaseSettings, SettingsConfigDict


class CollaborationSettings(BaseSettings):
    """Travail à plusieurs sur l'analyse de dossier (issue #118)."""

    # Durée d'un verrou d'élément sans renouvellement. Le frontend le renouvelle
    # tant que l'édition est active (toutes les ~20 s) : un instructeur qui part
    # sans enregistrer libère l'élément au bout de ce délai, sans action de sa part.
    ELEMENT_LOCK_TTL_SECONDS: int = 60
    # Une présence sans battement de cœur depuis ce délai n'est plus affichée.
    PRESENCE_TTL_SECONDS: int = 30
    # Fréquence de lecture du flux temps réel (SSE).
    LIVE_POLL_SECONDS: float = 1.5

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
