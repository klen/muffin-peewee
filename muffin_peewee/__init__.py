"""Support Peewee ORM for Muffin framework."""

import typing as t

import muffin
from aiopeewee import DatabaseAsync, db_url
from muffin.plugins import BasePlugin
from muffin.typing import Receive, Send
from peewee_migrate import Router

import peewee as pw

from .fields import Choices, JSONField

__version__ = "1.12.1"
__project__ = "muffin-peewee"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"


__all__ = "Plugin", "JSONField", "Choices"


assert JSONField and Choices


class Plugin(BasePlugin):

    """Muffin Peewee Plugin."""

    name = "peewee"
    defaults = {
        # Connection params
        "connection": "sqlite+async:///db.sqlite",
        "connection_params": {},
        # Manage connections automatically
        "manage_connections": True,
        # Setup migration engine
        "migrations_enabled": True,
        "migrations_path": "migrations",
    }
    router: Router

    def __init__(self, app: muffin.Application = None, **options):
        """Initialize the plugin."""
        self.database: pw.Proxy = pw.Proxy()
        self.models: t.Dict[str, pw.Model] = {}
        self.router: Router = None
        self.is_async: bool = False
        super(Plugin, self).__init__(app, **options)

    def setup(self, app: muffin.Application, **options):  # noqa
        """Init the plugin."""
        super().setup(app, **options)
        self.database.initialize(
            db_url.connect(self.cfg.connection, **self.cfg.connection_params)
        )
        if isinstance(self.database.obj, DatabaseAsync):
            self.is_async = True

        #  Hack for sqlite in memory (for tests)
        if self.is_async and self.database.obj.database == ":memory:":
            self.database.obj._state = pw._ConnectionLocal()

        if self.cfg.migrations_enabled:
            self.router = Router(self.database, migrate_dir=self.cfg.migrations_path)

            # Register migration commands
            @app.manage
            def peewee_migrate(name: str = None, fake: bool = False):
                """Run application's migrations.

                :param name: Choose a migration' name
                :param fake: Run as fake. Update migration history and don't touch the database
                """
                self.router.run(name, fake=fake)

            @app.manage
            def peewee_create(name: str = "auto", auto: bool = False):
                """Create a migration.

                :param name: Set name of migration [auto]
                :param auto: Track changes and setup migrations automatically
                """
                self.router.create(name, auto and [m for m in self.models.values()])

            @app.manage
            def peewee_rollback():
                """Rollback a migration.

                :param name: Migration name (actually it always should be a last one)
                """
                self.router.rollback()

            @app.manage
            def peewee_list():
                """List migrations."""
                self.router.logger.info("Migrations are done:")
                self.router.logger.info("\n".join(self.router.done))
                self.router.logger.info("")
                self.router.logger.info("Migrations are undone:")
                self.router.logger.info("\n".join(self.router.diff))

            @app.manage
            def peewee_clear():
                """Clear migrations from DB."""
                self.router.clear()

            @app.manage
            def peewee_merge(name: str = "initial", clear: bool = False):
                """Merge all migrations into one."""
                self.router.merge(name)

        if self.cfg.manage_connections:
            app.middleware(self.__middleware__, insert_first=True)

    def __getattr__(self, name: str) -> t.Any:
        """Proxy attrs to self database."""
        return getattr(self.database.obj, name)

    async def __aenter__(self):
        """Connect and enter the database context."""
        database = self.database
        if self.is_async:
            return await database.obj.__aenter__()

        database.connect(reuse_if_open=True)
        database.__enter__()
        return database.connection()

    async def __aexit__(self, *args):
        """Exit from the database context."""
        database = self.database
        if self.is_async:
            await database.obj.__aexit__(*args)

        else:
            database.__exit__(*args)
            database.close()

    async def __middleware__(
        self, handler: t.Callable, request: muffin.Request, receive: Receive, send: Send
    ):
        """Manage connections for request."""
        async with self as conn:
            try:
                response = await handler(request, receive, send)
                conn.commit()
                return response

            except pw.DatabaseError:
                conn.rollback()
                raise

    async def shutdown(self):
        """Close connections."""
        db = self.database.obj
        if self.is_async:
            await getattr(db, "close_all_async", getattr(db, "close_async"))()
        else:
            getattr(db, "close_all", getattr(db, "close"))()

    def register(self, model: pw.Model):
        """Register a model with the plugin."""
        self.models[model._meta.table_name] = model
        model._meta.database = self.database
        return model

    async def conftest(self):
        """Configure pytest tests."""
        for model in self.models.values():
            model.create_table()
