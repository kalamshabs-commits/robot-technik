from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys

config = context.config
fileConfig(config.config_file_name)

import importlib.util
import pathlib
models_path = pathlib.Path(__file__).resolve().parents[1] / 'cloud_api' / 'models.py'
spec = importlib.util.spec_from_file_location("rt_models", str(models_path))
rt_models = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(rt_models)
target_metadata = rt_models.Base.metadata

def run_migrations_offline():
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    section = config.get_section(config.config_ini_section)
    url = os.environ.get("DATABASE_URL") or section.get('sqlalchemy.url')
    connectable = engine_from_config({**section, 'sqlalchemy.url': url}, prefix='sqlalchemy.', poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()