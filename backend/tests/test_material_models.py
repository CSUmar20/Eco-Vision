from datetime import UTC, datetime

from app.models import (
    GENERAL_DISPOSAL_ACTIONS,
    GeneralDisposalRule,
    Material,
    MaterialAlias,
)


def test_general_disposal_actions_match_the_mvp_vocabulary() -> None:
    assert GENERAL_DISPOSAL_ACTIONS == (
        "reuse_or_donate",
        "recycle",
        "compost",
        "special_drop_off",
        "trash",
        "check_locally",
    )


def test_material_owns_aliases_and_country_guidance() -> None:
    material = Material(
        key="adhesive_tape",
        display_name="Adhesive tape",
        category="household_material",
    )
    alias = MaterialAlias(
        alias="Packing tape",
        normalized_alias="packing tape",
    )
    rule = GeneralDisposalRule(
        country_code="US",
        action="trash",
        headline="Put it in the trash",
        instructions="Place loose adhesive tape in household garbage.",
        preparation="Remove large amounts from recyclable cardboard.",
        warning=None,
        source_title="Official recycling guidance",
        source_url="https://example.gov/recycling",
        verified_at=datetime(2026, 10, 12, tzinfo=UTC),
    )

    material.aliases.append(alias)
    material.general_disposal_rules.append(rule)

    assert alias.material is material
    assert rule.material is material
