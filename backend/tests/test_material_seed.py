from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.material_catalog import MATERIAL_CATALOG
from app.models import GeneralDisposalRule, Material, MaterialAlias
from app.services.materials import normalize_material_alias, seed_material_catalog


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
    }

    with create_material_database() as database:
        seed_material_catalog(database)
        for classifier_label, expected_key in expected_materials.items():
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
