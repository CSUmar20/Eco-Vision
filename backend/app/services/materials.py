import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.material_catalog import MATERIAL_CATALOG, MaterialCatalogEntry
from app.models import (
    GENERAL_DISPOSAL_ACTIONS,
    GeneralDisposalRule,
    Material,
    MaterialAlias,
)


class MaterialCatalogError(ValueError):
    pass


@dataclass(frozen=True)
class MaterialSeedSummary:
    materials_created: int = 0
    aliases_created: int = 0
    rules_created: int = 0


VALID_ACTIONS: Final = frozenset(GENERAL_DISPOSAL_ACTIONS)


def normalize_material_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def resolve_material_aliases(
    database: Session,
    labels: Iterable[str],
) -> dict[str, Material]:
    normalized_by_label = {
        label: normalize_material_alias(label) for label in labels if label.strip()
    }

    if not normalized_by_label:
        return {}

    aliases = database.scalars(
        select(MaterialAlias)
        .join(MaterialAlias.material)
        .options(joinedload(MaterialAlias.material))
        .where(
            MaterialAlias.normalized_alias.in_(set(normalized_by_label.values())),
            Material.active.is_(True),
        )
    ).all()
    materials_by_normalized_alias = {
        alias.normalized_alias: alias.material for alias in aliases
    }

    return {
        label: material
        for label, normalized_alias in normalized_by_label.items()
        if (material := materials_by_normalized_alias.get(normalized_alias)) is not None
    }


def seed_material_catalog(
    database: Session,
    catalog: tuple[MaterialCatalogEntry, ...] = MATERIAL_CATALOG,
) -> MaterialSeedSummary:
    _validate_catalog(catalog)
    materials_created = 0
    aliases_created = 0
    rules_created = 0

    for entry in catalog:
        material = database.scalar(select(Material).where(Material.key == entry.key))

        if material is None:
            material = Material(
                key=entry.key,
                display_name=entry.display_name,
                category=entry.category,
                active=True,
            )
            database.add(material)
            database.flush()
            materials_created += 1
        else:
            material.display_name = entry.display_name
            material.category = entry.category
            material.active = True

        for alias_text in entry.aliases:
            normalized_alias = normalize_material_alias(alias_text)
            alias = database.scalar(
                select(MaterialAlias).where(
                    MaterialAlias.normalized_alias == normalized_alias
                )
            )

            if alias is None:
                database.add(
                    MaterialAlias(
                        material_id=material.id,
                        alias=alias_text,
                        normalized_alias=normalized_alias,
                    )
                )
                aliases_created += 1
            elif alias.material_id != material.id:
                raise MaterialCatalogError(
                    f"Alias {alias_text!r} is already assigned to another material."
                )
            else:
                alias.alias = alias_text

        rule = database.scalar(
            select(GeneralDisposalRule).where(
                GeneralDisposalRule.material_id == material.id,
                GeneralDisposalRule.country_code == entry.country_code,
            )
        )

        if rule is None:
            rule = GeneralDisposalRule(
                material_id=material.id,
                country_code=entry.country_code,
            )
            database.add(rule)
            rules_created += 1

        rule.action = entry.action
        rule.headline = entry.headline
        rule.instructions = entry.instructions
        rule.preparation = entry.preparation
        rule.warning = entry.warning
        rule.source_title = entry.source_title
        rule.source_url = entry.source_url
        rule.verified_at = entry.verified_at

    database.flush()

    return MaterialSeedSummary(
        materials_created=materials_created,
        aliases_created=aliases_created,
        rules_created=rules_created,
    )


def _validate_catalog(catalog: tuple[MaterialCatalogEntry, ...]) -> None:
    keys: set[str] = set()
    aliases: set[str] = set()

    for entry in catalog:
        if entry.key in keys:
            raise MaterialCatalogError(f"Duplicate material key: {entry.key!r}.")
        if entry.action not in VALID_ACTIONS:
            raise MaterialCatalogError(
                f"Unsupported action {entry.action!r} for {entry.key!r}."
            )
        if (
            len(entry.country_code) != 2
            or entry.country_code != entry.country_code.upper()
        ):
            raise MaterialCatalogError(
                f"Invalid country code {entry.country_code!r} for {entry.key!r}."
            )

        keys.add(entry.key)

        for alias_text in entry.aliases:
            normalized_alias = normalize_material_alias(alias_text)
            if not normalized_alias:
                raise MaterialCatalogError(f"Empty alias for {entry.key!r}.")
            if normalized_alias in aliases:
                raise MaterialCatalogError(
                    f"Duplicate normalized alias: {normalized_alias!r}."
                )
            aliases.add(normalized_alias)
