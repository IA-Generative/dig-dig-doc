"""Régénère le schéma de la base de données (docs/backend/data-model.png) à partir des modèles SQLAlchemy.

À relancer à chaque migration, et à commiter avec elle :

    cd backend && uv run --group dev python scripts/generate_data_model.py

Nécessite le groupe de dépendances « dev » (eralchemy2) et Graphviz (la commande `dot`).
Aucune base de données n'est utilisée : le schéma vient des modèles.
"""

from pathlib import Path

from eralchemy2 import render_er

from app.models import Base

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "backend" / "data-model.png"

if __name__ == "__main__":
    render_er(Base, str(OUTPUT))
    print(f"Schéma écrit dans {OUTPUT}")
