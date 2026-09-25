import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.cgu_acceptance_repository import CguAcceptanceRepository
from app.repositories.cgu_repository import CguRepository
from app.schemas.cgu import (
    CguAcceptanceStatus,
    CguAdminOut,
    CguCreate,
    CguOut,
    CguUpdate,
)

# ── Route publique (pas d'auth) ────────────────────────────────────────
public_router = APIRouter(prefix="/cgu", tags=["CGU"])


@public_router.get("", response_model=CguOut)
async def get_active_cgu(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CguOut:
    """Récupère la version active des CGU. Route publique."""
    cgu = await CguRepository(db).get_active()
    if cgu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune CGU active")
    return cgu


@public_router.get("/acceptance", response_model=CguAcceptanceStatus)
async def get_acceptance_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> CguAcceptanceStatus:
    """Indique si l'utilisateur courant a accepté la version active des CGU.

    Si aucune version n'est active, renvoie ``accepted=True`` et ``cgu=None``
    (pas de CGU à accepter). Sinon, renvoie la version active et un booléen
    ``accepted`` indiquant si l'utilisateur l'a acceptée.
    """
    cgu = await CguRepository(db).get_active()
    if cgu is None:
        return CguAcceptanceStatus(accepted=True, cgu=None)

    accepted = await CguAcceptanceRepository(db).has_accepted(user_id=user.user_id, cgu_id=cgu.id)
    return CguAcceptanceStatus(accepted=accepted, cgu=CguOut.model_validate(cgu))


@public_router.post("/acceptance", response_model=CguAcceptanceStatus, status_code=status.HTTP_200_OK)
async def accept_cgu(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> CguAcceptanceStatus:
    """Enregistre l'acceptation de la version active des CGU par l'utilisateur.

    Idempotente : accepter deux fois ne provoque pas d'erreur. Si aucune
    version n'est active, renvoie ``accepted=True`` et ``cgu=None``.
    """
    cgu = await CguRepository(db).get_active()
    if cgu is None:
        return CguAcceptanceStatus(accepted=True, cgu=None)

    await CguAcceptanceRepository(db).accept(user_id=user.user_id, cgu_id=cgu.id)
    return CguAcceptanceStatus(accepted=True, cgu=CguOut.model_validate(cgu))


# ── Routes admin (auth + is_admin) ────────────────────────────────────
admin_router = APIRouter(prefix="/admin/cgu", tags=["Admin"], dependencies=[Depends(get_current_user)])


def _require_admin(user: RequestContext) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )


@admin_router.get("/versions", response_model=list[CguAdminOut])
async def list_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> list[CguAdminOut]:
    _require_admin(user)
    versions = await CguRepository(db).list_all()
    return [CguAdminOut.model_validate(v) for v in versions]


@admin_router.post("", response_model=CguAdminOut, status_code=status.HTTP_201_CREATED)
async def create_version(
    body: CguCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> CguAdminOut:
    _require_admin(user)
    cgu = await CguRepository(db).create(content=body.content, created_by=user.user_id)
    return CguAdminOut.model_validate(cgu)


@admin_router.patch("/{cgu_id}", response_model=CguAdminOut)
async def update_version(
    cgu_id: uuid.UUID,
    body: CguUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> CguAdminOut:
    _require_admin(user)
    repository = CguRepository(db)
    cgu = await repository.get(cgu_id)
    if cgu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable")
    if cgu.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de modifier une version déjà publiée",
        )
    updated = await repository.update_content(cgu, body.content)
    return CguAdminOut.model_validate(updated)


@admin_router.post("/{cgu_id}/activate", response_model=CguAdminOut)
async def activate_version(
    cgu_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> CguAdminOut:
    _require_admin(user)
    repository = CguRepository(db)
    cgu = await repository.get(cgu_id)
    if cgu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable")
    activated = await repository.activate(cgu)
    return CguAdminOut.model_validate(activated)
