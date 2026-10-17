from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.material_catalog import MATERIAL_CATALOG
from app.models import GeneralDisposalRule, Material, MaterialAlias
from app.services.classifier import CANDIDATE_LABELS
from app.services.materials import (
    get_general_disposal_rule,
    normalize_material_alias,
    resolve_material_aliases,
    seed_material_catalog,
)


def create_material_database() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Material.__table__.create(engine)
    MaterialAlias.__table__.create(engine)
    GeneralDisposalRule.__table__.create(engine)
    return Session(engine)


def test_seed_catalog_matches_classifier_materials_and_is_idempotent() -> None:
    with create_material_database() as database:
        first_summary = seed_material_catalog(database)
        database.commit()
        second_summary = seed_material_catalog(database)
        database.commit()

        assert first_summary.materials_created == len(MATERIAL_CATALOG)
        assert first_summary.rules_created == len(MATERIAL_CATALOG)
        assert second_summary.materials_created == 0
        assert second_summary.aliases_created == 0
        assert second_summary.rules_created == 0
        assert database.scalar(select(func.count()).select_from(Material)) == len(
            MATERIAL_CATALOG
        )
        assert database.scalar(
            select(func.count()).select_from(GeneralDisposalRule)
        ) == len(MATERIAL_CATALOG)


def test_catalog_contains_selected_household_materials() -> None:
    assert len(MATERIAL_CATALOG) == 25
    assert len(CANDIDATE_LABELS) == 26
    assert CANDIDATE_LABELS[-1] == "another type of household object"


def test_every_general_rule_has_a_verified_authoritative_source() -> None:
    authoritative_domains = {
        "city.milwaukee.gov",
        "recyclesmartma.org",
        "www.epa.gov",
        "www.fda.gov",
        "www.stpaul.gov",
        "zerowastesonoma.gov",
    }

    for entry in MATERIAL_CATALOG:
        parsed_url = urlparse(entry.source_url)

        assert entry.source_title.strip(), entry.key
        assert parsed_url.scheme == "https", entry.key
        assert parsed_url.hostname in authoritative_domains, entry.key
        assert entry.verified_at.tzinfo is not None, entry.key
        assert entry.verified_at <= datetime.now(UTC), entry.key


def test_classifier_aliases_resolve_to_canonical_materials() -> None:
    expected_materials = {
        "an aluminum beverage can": "aluminum_beverage_can",
        "a metal food can": "metal_food_can",
        "a clear glass bottle or jar": "glass_bottle_or_jar",
        "a cardboard box": "corrugated_cardboard_box",
        "a sheet of paper": "paper_sheet",
        "a clear plastic beverage bottle": "plastic_beverage_bottle",
        "an opaque plastic jug or container": "rigid_plastic_container",
        "a plastic bag or plastic film": "plastic_bag_or_film",
        "a polystyrene foam container": "polystyrene_foam_container",
        "food waste": "food_scraps",
        "a household battery": "household_battery",
        "an electronic device": "consumer_electronic_device",
        "clothing or textile": "reusable_clothing_or_textile",
        "mixed-material packaging": "mixed_material_packaging",
        "adhesive tape": "adhesive_tape",
        "aluminum foil or tray": "aluminum_foil_or_tray",
        "a pizza box": "pizza_box",
        "a disposable paper cup or takeout container": (
            "paper_cup_or_takeout_container"
        ),
        "a food or beverage carton": "food_or_beverage_carton",
        "a ceramic dish or drinking glass": "ceramic_dish_or_drinking_glass",
        "a plastic utensil or straw": "plastic_utensil_or_straw",
        "yard trimmings": "yard_trimmings",
        "a CFL or fluorescent light bulb": "cfl_or_fluorescent_bulb",
        "a paint or solvent container": "paint_or_solvent_container",
        "a needle or medical sharp": "needle_or_medical_sharp",
    }

    assert set(CANDIDATE_LABELS[:-1]) == set(expected_materials)

    with create_material_database() as database:
        seed_material_catalog(database)
        resolved_materials = resolve_material_aliases(database, CANDIDATE_LABELS)

        assert set(resolved_materials) == set(CANDIDATE_LABELS[:-1])

        for classifier_label, expected_key in expected_materials.items():
            assert resolved_materials[classifier_label].key == expected_key

            alias = database.scalar(
                select(MaterialAlias).where(
                    MaterialAlias.normalized_alias
                    == normalize_material_alias(classifier_label)
                )
            )

            assert alias is not None
            assert alias.material.key == expected_key

        unknown_alias = database.scalar(
            select(MaterialAlias).where(
                MaterialAlias.normalized_alias
                == normalize_material_alias("another type of household object")
            )
        )
        assert unknown_alias is None


def test_material_alias_resolution_normalizes_classifier_labels() -> None:
    label = "  A CARDBOARD BOX  "

    with create_material_database() as database:
        seed_material_catalog(database)

        resolved_materials = resolve_material_aliases(database, [label, "   "])

        assert resolved_materials[label].key == "corrugated_cardboard_box"


def test_general_guidance_is_loaded_by_material_and_country() -> None:
    with create_material_database() as database:
        seed_material_catalog(database)
        material = resolve_material_aliases(database, ["a cardboard box"])[
            "a cardboard box"
        ]

        rule = get_general_disposal_rule(database, material.id, "US")

        assert rule is not None
        assert rule.action == "recycle"
        assert rule.material_id == material.id
        assert get_general_disposal_rule(database, material.id, "CA") is None
