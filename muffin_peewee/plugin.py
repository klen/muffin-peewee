"""Implement the plugin."""

import peewee as pw

from muffin.plugins import BasePlugin
from muffin.utils import Struct
from peewee_migrate import Router

from .models import Model, TModel
from .mpeewee import connect, AIODatabase


class Plugin(BasePlugin):

    """Integrate Peewee to Muffin."""

    name = 'peewee'
    defaults = {

        # Connection params
        'connection': 'sqlite:///db.sqlite',
        'connection_params': {},

        # Manage connections manually
        'connection_manual': False,

        # Setup migration engine
        'migrations_enabled': True,
        'migrations_path': 'migrations',
    }

    Model = Model
    TModel = TModel

    def __init__(self, app=None, **options):
        """Initialize the plugin."""
        self.database = pw.Proxy()
        self.models = Struct()
        self.router = None

        super().__init__(app, **options)

    def setup(self, app):  # noqa
        """Initialize the application."""
        super().setup(app)

        # Setup Database
        self.database.initialize(connect(self.cfg.connection, **self.cfg.connection_params))

        # Fix SQLite in-memory database
        if self.database.database == ':memory:':
            self.cfg.connection_manual = True

        if not self.cfg.migrations_enabled:
            return

        # Setup migration engine
        self.router = Router(self.database, migrate_dir=self.cfg.migrations_path)

        # Register migration commands
        def pw_migrate(name: str=None, fake: bool=False):
            """Run application's migrations.

            :param name: Choose a migration' name
            :param fake: Run as fake. Update migration history and don't touch the database
            """
            self.router.run(name, fake=fake)

        self.app.manage.command(pw_migrate)

        def pw_rollback(name: str=None):
            """Rollback a migration.

            :param name: Migration name (actually it always should be a last one)
            """
            if not name:
                name = self.router.done[-1]
            self.router.rollback(name)

        self.app.manage.command(pw_rollback)

        def pw_create(name: str='auto', auto: bool=False):
            """Create a migration.

            :param name: Set name of migration [auto]
            :param auto: Track changes and setup migrations automatically
            """
            if auto:
                auto = list(self.models.values())
            self.router.create(name, auto)

        self.app.manage.command(pw_create)

        def pw_list():
            """List migrations."""
            self.router.logger.info('Migrations are done:')
            self.router.logger.info('\n'.join(self.router.done))
            self.router.logger.info('')
            self.router.logger.info('Migrations are undone:')
            self.router.logger.info('\n'.join(self.router.diff))

        self.app.manage.command(pw_list)

        @self.app.manage.command
        def pw_merge():
            """Merge migrations into one."""
            self.router.merge()

        self.app.manage.command(pw_merge)

    def startup(self, app):
        """Register connection's middleware and prepare self database."""
        self.database.init_async(app.loop)
        if not self.cfg.connection_manual:
            app.middlewares.insert(0, self._middleware)

    def cleanup(self, app):
        """Close all connections."""
        if hasattr(self.database.obj, 'close_all'):
            self.database.close_all()

    async def _middleware(self, request, handler):
        await self.database.async_connect()

        try:
            response = await handler(request)
            self.database.commit()
            return response

        except pw.DatabaseError:
            self.database.rollback()
            raise

        finally:
            if not self.database.is_closed():
                await self.database.async_close()

    _middleware.__middleware_version__ = 1

    def register(self, model):
        """Register a model in self."""
        self.models[model._meta.table_name] = model
        model._meta.database = self.database
        return model

    async def manage(self):
        """Manage a database connection."""
        cm = _ContextManager(self.database)
        if isinstance(self.database.obj, AIODatabase):
            cm.connection = await self.database.async_connect()

        else:
            cm.connection = self.database.connect()

        return cm

    async def conftest(self):
        """Integration with tests."""
        for model in self.models.values():
            try:
                model.create_table()
            except pw.OperationalError:
                pass


class _ContextManager:

    """Context manager.

    This enables the following idiom for acquiring and releasing a database around a block:

        with (yield from database):
            <block>
    """

    def __init__(self, db):
        self.transaction = pw._transaction(db)
        self.connection = None

    def __enter__(self):
        self.transaction.__enter__()
        return self

    def __exit__(self, *args):
        try:
            self.transaction.__exit__(*args)
        finally:
            if self.connection:
                self.connection.close()

#  pylama:ignore=W0212
