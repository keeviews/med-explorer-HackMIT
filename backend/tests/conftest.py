import pytest

from app.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
def fresh_seed():
    """Run every test against the current data/seed.json, not a stale local database."""
    seed_database()
