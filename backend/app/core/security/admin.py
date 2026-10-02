from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.security.factory import RequestContext, get_current_user


def require_admin(user: Annotated[RequestContext, Depends(get_current_user)]) -> RequestContext:
    """Dépendance des routes d'administration : réservées aux administrateurs."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    return user
