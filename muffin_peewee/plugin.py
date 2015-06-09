import asyncio
import concurrent
from functools import partial
from contextlib import contextmanager

import peewee as pw
from muffin.plugins import BasePlugin
from muffin.utils import Structure, MuffinException
from playhouse.csv_utils import dump_csv, load_csv
from playhouse.db_url import urlparse, parseresult_to_dict, schemes

from .models import Model, TModel
from .migrate import Router, MigrateHistory
from .serialize import Serializer


pw.SqliteDatabase.register_fields({'uuid': 'UUID'})


class Plugin(BasePlugin):

    """ Integrate peewee to Muffin. """

    name = 'peewee'
    defaults = {
        'connection': 'sqlite:///db.sqlite',
        'connection_manual': False,
        'connection_params': {},
        'max_connections': 2,
        'migrations_enabled': True,
        'migrations_path': 'migrations',
    }

    Model = Model
    TModel = TModel

    def __init__(self, **options):
        super().__init__(**options)

        self.database = pw.Proxy()
        self.serializer = Serializer()
        self.models = Structure()

    def setup(self, app):
        """ Initialize the application. """
        super().setup(app)

        # Setup Database
        self.database.initialize(connect(
            self.options.connection, **self.options.connection_params))

        self.threadpool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.options.max_connections)

        if not self.options.migrations_enabled:
            return

        # Setup migration engine
        self.router = Router(self)
        self.register(MigrateHistory)

        # Register migration commands
        @self.app.manage.command
        def migrate(name: str=None):
            """ Run application's migrations.

            :param name: Choose a migration' name

            """
            self.router.run(name)

        @self.app.manage.command
        def create(name: str):
            """ Create a migration.

            :param name: Set name of migration [auto]

            """
            self.router.create(name)

        @self.app.manage.command
        def csv_dump(table: str, path: str='dump.csv'):
            """ Dump DB table to CSV.

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
            """ Load CSV to DB table.

            :param table: Table name for load data
            :param path: Path to file which from data will be loaded
            :param pk_in_csv: Primary keys stored in CSV

            """
            model = self.models.get(table)
            if model is None:
                raise MuffinException('Unknown db table: %s' % table)

            load_csv(model, path)
            self.app.logger.info('Loaded from %s' % path)

    @contextmanager
    def manage(self):
        """ Manage a database connection. """
        try:
            yield self.database.connect()
        finally:
            self.database.commit()
            if not self.database.is_closed():
                self.database.close()

    @asyncio.coroutine
    def middleware_factory(self, app, handler):
        """ Manage a database connection while request is processing. """
        @asyncio.coroutine
        def middleware(request):
            try:
                if not (self.options.connection_manual or self.options.connection.startswith('sqlite')): # noqa
                    with self.manage():
                        return (yield from handler(request))

                return (yield from handler(request))

            except pw.DatabaseError:
                self.database.rollback()
                raise

        return middleware

    def query(self, query):
        if isinstance(query, pw.SelectQuery):
            return self.run(lambda: list(query))
        return self.run(query.execute)

    @asyncio.coroutine
    def run(self, function, *args, **kwargs):
        """ Run sync code asyncronously. """
        if kwargs:
            function = partial(function, **kwargs)

        def iteration(database, *args):
            database.connect()
            try:
                with database.transaction():
                    return function(*args)
            except pw.PeeweeException:
                database.rollback()
                raise
            finally:
                database.commit()

        return (
            yield from self.app.loop.run_in_executor(
                self.threadpool, iteration, self.database,  *args))

    def to_dict(self, obj, **kwargs):
        return self.serializer.serialize_object(obj, **kwargs)

    def register(self, model):
        """ Register a model in self. """
        self.models[model._meta.db_table] = model
        model._meta.database = self.database
        return model


# TODO: Remove when peewee > 2.6.1 will be released
def connect(url, **connect_params):
    parsed = urlparse(url)
    connect_kwargs = parseresult_to_dict(parsed)
    connect_kwargs.update(connect_params)
    database_class = schemes.get(parsed.scheme)

    if database_class is None:
        if database_class in schemes:
            raise RuntimeError('Attempted to use "%s" but a required library '
                               'could not be imported.' % parsed.scheme)
        else:
            raise RuntimeError('Unrecognized or unsupported scheme: "%s".' %
                               parsed.scheme)

    return database_class(**connect_kwargs)
