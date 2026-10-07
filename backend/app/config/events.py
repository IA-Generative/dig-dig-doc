from pydantic_settings import BaseSettings, SettingsConfigDict


class DossierEventSettings(BaseSettings):
    """Journal d'événements du dossier (issue #169)."""

    # Une consultation n'est enregistrée qu'une fois par utilisateur dans cette fenêtre : sans ça, chaque
    # rechargement de page remplirait le journal.
    CONSULTATION_DEDUP_MINUTES: int = 15

    model_config = SettingsConfigDict(case_sensitive=True, env_file=(".env", ".env.local"), extra="ignore")
