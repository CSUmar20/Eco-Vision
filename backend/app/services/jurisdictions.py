from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import DisposalRule, Jurisdiction, JurisdictionPostalCode


def search_jurisdictions(
    database: Session,
    query: str,
    limit: int,
) -> list[Jurisdiction]:
    text_match = or_(
        Jurisdiction.slug.icontains(query, autoescape=True),
        Jurisdiction.name.icontains(query, autoescape=True),
        Jurisdiction.display_name.icontains(query, autoescape=True),
        Jurisdiction.state_code.icontains(query, autoescape=True),
        Jurisdiction.county_name.icontains(query, autoescape=True),
        Jurisdiction.waste_provider.icontains(query, autoescape=True),
    )
    postal_code_match = JurisdictionPostalCode.postal_code.startswith(
        query,
        autoescape=True,
    )
    statement = (
        select(Jurisdiction)
        .outerjoin(JurisdictionPostalCode)
        .options(selectinload(Jurisdiction.postal_codes))
        .where(
            Jurisdiction.active.is_(True),
            or_(text_match, postal_code_match),
        )
        .distinct()
        .order_by(Jurisdiction.display_name)
        .limit(limit)
    )

    return list(database.scalars(statement).unique().all())


def get_jurisdiction(
    database: Session,
    jurisdiction_id: UUID,
) -> Jurisdiction | None:
    statement = (
        select(Jurisdiction)
        .options(selectinload(Jurisdiction.postal_codes))
        .where(
            Jurisdiction.id == jurisdiction_id,
            Jurisdiction.active.is_(True),
        )
    )

    return database.scalars(statement).one_or_none()


def get_disposal_rules(
    database: Session,
    jurisdiction_id: UUID,
) -> list[DisposalRule]:
    statement = (
        select(DisposalRule)
        .where(DisposalRule.jurisdiction_id == jurisdiction_id)
        .order_by(DisposalRule.material_key)
    )

    return list(database.scalars(statement).all())
