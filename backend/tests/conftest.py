import os

# Application settings are constructed during module import. Unit tests replace
# database sessions, but SQLAlchemy still needs a valid URL to create its engine.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://localhost/ecovision_test",
)
