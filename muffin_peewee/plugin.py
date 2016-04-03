"""Implement the plugin."""

import asyncio

import peewee
from muffin.plugins import BasePlugin
from muffin.utils import Struct, MuffinException
from playhouse.csv_utils import dump_csv, load_csv
from peewee_migrate import Router

from .models import Model, TModel
from .mpeewee import connect, AIODatabase


@asyncio.coroutine
def peewee_middleware_factory(app, handler):
    """Manage a database connection while request is processing."""
    database = app.ps.peewee.database

    @asyncio.coroutine
    def middleware(request):
        yield from database.async_connect()

        try:
            response = yield from handler(request)
            database.commit()
            return response

        except peewee.DatabaseError:
            database.rollback()
            raise

        finally:
            if not database.is_closed():
                yield from database.async_close()

    return middleware


class _ContextManager:

    """Context manager.

    This enables the following idiom for acquiring and releasing a database around a block:

        with (yield from database):
            <block>
    """

    def __init__(self, db):
        self._db = db
        self._db.push_execution_context(self)

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        try:
            self._db.commit()
        except peewee.DatabaseError:
            self._db.rollback()

        finally:
            self._db.pop_execution_context()
            self._db._close(self.connection)
            self._db = None


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

    def __init__(self, **options):
        """Initialize the plugin."""
        super().__init__(**options)

        self.database = peewee.Proxy()
        self.models = Struct()

    def setup(self, app):
        """Initialize the application."""
        super().setup(app)

        # Setup Database
        self.database.initialize(connect(
            self.cfg.connection, **self.cfg.connection_params))

        # Fix SQLite in-memory database
        if self.database.database == ':memory:':
            self.cfg.connection_manual = True

        if not self.cfg.migrations_enabled:
            return

        # Setup migration engine
        self.router = Router(self.database, migrate_dir=self.cfg.migrations_path)

        # Register migration commands
        @self.app.manage.command
        def migrate(name: str=None, fake: bool=False):
            """Run application's migrations.

            :param name: Choose a migration' name
            :param fake: Run as fake. Update migration history and don't touch the database
            """
            self.router.run(name, fake=fake)

        @self.app.manage.command
        def create(name: str='auto', auto: bool=False):
            """Create a migration.

            :param name: Set name of migration [auto]
            :param auto: Track changes and setup migrations automatically
            """
            if auto:
                auto = list(self.models.values())
            self.router.create(name, auto)

        @self.app.manage.command
        def rollback(name: str):
            """Rollback a migration.

            :param name: Migration name (actually it always should be a last one)
            """
            self.router.rollback(name)

        @self.app.manage.command
        def csv_dump(table: str, path: str='dump.csv'):
            """Dump DB table to CSV.

            :param table: Table name for dump data
            :param path: Path to file where data will be dumped
            """
            model = self.models.get(table)
            if model is None:
                raise MuffinException('Unknown db table: %s' % table)

            with open(path, 'w') as fh:
                dump_csv(model.select().order_by(model._meta.primary_key), fh)
                self.app.logger.info('Dumped to %s' % path)

        @self.app.manage.command
        def csv_load(table: str, path: str='dump.csv', pk_in_csv: bool=False):
            """Load CSV to DB table.

            :param table: Table name for load data
            :param path: Path to file which from data will be loaded
            :param pk_in_csv: Primary keys stored in CSV
            """
            model = self.models.get(table)
            if model is None:
                raise MuffinException('Unknown db table: %s' % table)

            load_csv(model, path)
            self.app.logger.info('Loaded from %s' % path)

    def start(self, app):
        """Register connection's middleware and prepare self database."""
        self.database.async_init(app.loop)
        if not self.cfg.connection_manual:
            app.middlewares.insert(0, peewee_middleware_factory)

    def finish(self, app):
        """Close all connections."""
        if hasattr(self.database.obj, 'close_all'):
            self.database.close_all()

    def register(self, model):
        """Register a model in self."""
        self.models[model._meta.db_table] = model
        model._meta.database = self.database
        return model

    @asyncio.coroutine
    def manage(self):
        """Manage a database connection."""
        cm = _ContextManager(self.database)
        if (self.database.obj, AIODatabase):
            cm.connection = yield from self.database.async_connect()

        else:
            cm.connection = self.database.connect()

        return cm


#    def query(self, query):
#        """ Async query. """
#        if isinstance(query, pw.SelectQuery):
#            return self.run(lambda: list(query))
#        return self.run(query.execute)
#
#    @asyncio.coroutine
#    def run(self, function, *args, **kwargs):
#        """ Run sync code asyncronously. """
#        if kwargs:
#            function = partial(function, **kwargs)
#
#        def iteration(database, *args):
#            database.connect()
#            try:
#                with database.transaction():
#                    return function(*args)
#            except pw.PeeweeException:
#                database.rollback()
#                raise
#            finally:
#                database.commit()
#
#        return (
#            yield from self.app.loop.run_in_executor(
#                self.threadpool, iteration, self.database,  *args))
