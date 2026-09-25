from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.modules.etablissements import models as etablissements_models  # noqa: F401
from app.modules.identite import models as identite_models  # noqa: F401
from app.modules.inscriptions import models as inscriptions_models  # noqa: F401
from app.modules.recrutement import models as recrutement_models  # noqa: F401
from app.modules.pedagogie import models as pedagogie_models  # noqa: F401
from app.modules.evaluations import models as evaluations_models  # noqa: F401
from app.modules.actes import models as actes_models  # noqa: F401
from app.modules.controle_acces import models as controle_acces_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
