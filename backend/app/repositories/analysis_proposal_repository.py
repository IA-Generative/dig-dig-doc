"""Propositions de modification de l'analyse de dossier (issue #114).

Règles portées ici :
- une proposition n'applique rien : seule une décision humaine (accepter,
  modifier) crée une version, dans la **même transaction** que le changement
  de statut et l'écriture du journal ;
- une proposition sur un élément modifié depuis (version retenue différente de
  celle vue à la proposition) est signalée (``StaleProposalError``) plutôt
  qu'appliquée ;
- seule une proposition en attente peut être décidée, une seule fois (verrou
  de ligne pendant la décision).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.analysis_proposal import (
    AnalysisProposal,
    AnalysisProposalEvent,
    ProposalEventKind,
    ProposalStatus,
)
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    DossierAnalysis,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.schemas.dossier_analysis import validate_element_value


class StaleProposalError(Exception):
    """L'élément a été modifié depuis la proposition."""


class ProposalAlreadyDecidedError(Exception):
    pass


class ProposalTargetError(Exception):
    """L'élément visé n'existe pas dans cette analyse."""


class AnalysisProposalRepository:
    def __init__(self, analyses: DossierAnalysisRepository) -> None:
        self.analyses = analyses
        self.db = analyses.db

    # --- Lecture ---

    async def list_proposals(
        self, analysis_id: uuid.UUID, status: ProposalStatus | None = None
    ) -> list[AnalysisProposal]:
        query = select(AnalysisProposal).where(AnalysisProposal.analysis_id == analysis_id)
        if status is not None:
            query = query.where(AnalysisProposal.status == status)
        result = await self.db.execute(query.order_by(AnalysisProposal.created_at.desc(), AnalysisProposal.id))
        return list(result.scalars().all())

    async def get(self, analysis_id: uuid.UUID, proposal_id: uuid.UUID) -> AnalysisProposal | None:
        result = await self.db.execute(
            select(AnalysisProposal).where(
                AnalysisProposal.id == proposal_id, AnalysisProposal.analysis_id == analysis_id
            )
        )
        return result.scalar_one_or_none()

    async def list_events(self, proposal_id: uuid.UUID) -> list[AnalysisProposalEvent]:
        result = await self.db.execute(
            select(AnalysisProposalEvent)
            .where(AnalysisProposalEvent.proposal_id == proposal_id)
            .order_by(AnalysisProposalEvent.created_at, AnalysisProposalEvent.id)
        )
        return list(result.scalars().all())

    # --- Création ---

    async def create(
        self,
        analysis: DossierAnalysis,
        *,
        proposed_by: str,
        value: dict[str, Any],
        reason: str,
        element_id: uuid.UUID | None = None,
        kind: AnalysisElementKind | None = None,
        definition_name: str | None = None,
        source_type: str | None = None,
        source_id: uuid.UUID | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> AnalysisProposal:
        """Enregistre une proposition en attente. N'applique rien. Lève
        ProposalTargetError si l'élément visé n'est pas dans l'analyse, et
        InvalidElementValueError si la valeur ne correspond pas au type."""
        base_version_id: uuid.UUID | None = None
        if element_id is not None:
            element = await self.analyses.get_element(analysis.id, element_id)
            if element is None:
                raise ProposalTargetError("Élément introuvable dans cette analyse")
            kind = element.kind
            definition_name = definition_name or element.definition_name
            base_version_id = element.retained_version_id
        assert kind is not None  # garanti par le schéma d'entrée
        clean_value = validate_element_value(kind, value)
        proposal = AnalysisProposal(
            analysis_id=analysis.id,
            element_id=element_id,
            kind=kind,
            definition_name=definition_name,
            base_version_id=base_version_id,
            proposed_value=clean_value,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            proposed_by=proposed_by,
            model=model,
            prompt_version=prompt_version,
            status=ProposalStatus.PENDING,
        )
        self.db.add(proposal)
        await self.db.flush()
        self._log(proposal, ProposalEventKind.PROPOSED, actor_id=proposed_by, value=clean_value, note=reason)
        await self.db.commit()
        return proposal

    # --- Décisions ---

    async def accept(self, analysis: DossierAnalysis, proposal_id: uuid.UUID, *, user_id: str) -> AnalysisProposal:
        """Accepte la proposition telle quelle : crée une version (ou un
        élément) avec la valeur proposée."""
        return await self._decide(analysis, proposal_id, user_id=user_id, value=None, note=None, rejected=False)

    async def modify(
        self,
        analysis: DossierAnalysis,
        proposal_id: uuid.UUID,
        *,
        user_id: str,
        value: dict[str, Any],
        note: str | None,
    ) -> AnalysisProposal:
        """Accepte avec une autre valeur que celle proposée."""
        return await self._decide(analysis, proposal_id, user_id=user_id, value=value, note=note, rejected=False)

    async def reject(
        self, analysis: DossierAnalysis, proposal_id: uuid.UUID, *, user_id: str, note: str | None
    ) -> AnalysisProposal:
        return await self._decide(analysis, proposal_id, user_id=user_id, value=None, note=note, rejected=True)

    async def _decide(
        self,
        analysis: DossierAnalysis,
        proposal_id: uuid.UUID,
        *,
        user_id: str,
        value: dict[str, Any] | None,
        note: str | None,
        rejected: bool,
    ) -> AnalysisProposal:
        # Verrou de ligne : deux décisions simultanées ne s'appliquent pas deux fois.
        result = await self.db.execute(
            select(AnalysisProposal)
            .where(AnalysisProposal.id == proposal_id, AnalysisProposal.analysis_id == analysis.id)
            .with_for_update()
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ProposalTargetError("Proposition introuvable")
        if proposal.status != ProposalStatus.PENDING:
            await self.db.rollback()
            raise ProposalAlreadyDecidedError()

        now = datetime.now(UTC)
        duration = (now - proposal.created_at).total_seconds()
        modified = value is not None
        final_value = proposal.proposed_value if value is None else validate_element_value(proposal.kind, value)

        if rejected:
            event_kind, status = ProposalEventKind.REJECTED, ProposalStatus.REJECTED
            final_value = proposal.proposed_value
        else:
            event_kind = ProposalEventKind.MODIFIED if modified else ProposalEventKind.ACCEPTED
            status = ProposalStatus.MODIFIED if modified else ProposalStatus.ACCEPTED
            try:
                await self._apply(analysis, proposal, final_value, user_id=user_id)
            except StaleProposalError:
                await self.db.rollback()
                raise

        proposal.status = status
        proposal.decided_by = user_id
        proposal.decided_at = now
        self._log(proposal, event_kind, actor_id=user_id, value=final_value, note=note, duration=duration)
        await self.db.commit()
        return proposal

    async def _apply(
        self, analysis: DossierAnalysis, proposal: AnalysisProposal, value: dict[str, Any], *, user_id: str
    ) -> None:
        """Crée la version (ou l'élément) correspondant à la décision, sans
        valider la transaction : l'appelant le fait avec le statut et le journal."""
        if proposal.element_id is None:
            element = await self.analyses.create_element(
                analysis,
                kind=proposal.kind,
                value=value,
                origin=ElementVersionOrigin.INSTRUCTOR,
                definition_name=proposal.definition_name,
                author_id=user_id,
                reason=proposal.reason,
                source_type="proposal",
                source_id=proposal.id,
                commit=False,
            )
            proposal.resulting_element_id = element.id
            proposal.resulting_version_id = element.retained_version_id
            return
        element = await self.db.get(AnalysisElement, proposal.element_id, with_for_update=True)
        if element is None:
            raise ProposalTargetError("Élément introuvable dans cette analyse")
        if element.retained_version_id != proposal.base_version_id:
            raise StaleProposalError()
        version = await self.analyses.add_version(
            element,
            value=value,
            origin=ElementVersionOrigin.INSTRUCTOR,
            author_id=user_id,
            reason=proposal.reason,
            source_type="proposal",
            source_id=proposal.id,
            commit=False,
        )
        proposal.resulting_version_id = version.id
        proposal.resulting_element_id = element.id

    def _log(
        self,
        proposal: AnalysisProposal,
        kind: ProposalEventKind,
        *,
        actor_id: str,
        value: dict[str, Any],
        note: str | None,
        duration: float | None = None,
    ) -> None:
        self.db.add(
            AnalysisProposalEvent(
                proposal_id=proposal.id,
                kind=kind,
                actor_id=actor_id,
                value=value,
                note=note,
                duration_seconds=duration,
                model=proposal.model,
                prompt_version=proposal.prompt_version,
            )
        )
