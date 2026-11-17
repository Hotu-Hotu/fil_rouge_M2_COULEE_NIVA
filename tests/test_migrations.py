"""Les migrations Alembic s'appliquent et s'annulent, et correspondent aux modeles."""

import os
import subprocess
import sys


def alembic(database_url, *args):
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], env=env, capture_output=True, text=True, check=True
    )


def test_upgrade_downgrade_and_models_in_sync(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'migrations.db'}"
    alembic(url, "upgrade", "head")
    # aucune difference entre les modeles et le schema obtenu par les migrations
    alembic(url, "check")
    alembic(url, "downgrade", "base")
