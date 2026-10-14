from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.services.materials import MaterialCatalogError, seed_material_catalog


def main() -> None:
    with SessionLocal() as database:
        try:
            summary = seed_material_catalog(database)
            database.commit()
        except (MaterialCatalogError, SQLAlchemyError) as error:
            database.rollback()
            raise SystemExit("The material catalog could not be seeded.") from error

    print(
        "Material catalog synchronized: "
        f"{summary.materials_created} materials, "
        f"{summary.aliases_created} aliases, "
        f"{summary.rules_created} rules created."
    )


if __name__ == "__main__":
    main()
