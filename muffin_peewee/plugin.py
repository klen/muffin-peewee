import asyncio
import concurrent
from functools import partial

import peewee as pw
from muffin.plugins import BasePlugin
from muffin.utils import Structure
from playhouse.db_url import connect

from .models import Model, TModel
from .migrate import Router, MigrateHistory
from .serialize import Serializer


class Plugin(BasePlugin):

    """ Integrate peewee to Muffin. """

    name = 'peewee'
    defaults = {
        'connection': 'sqlite:///db.sqlite',
        'max_connections': 2,
        'migrations_enabled': True,
        'migrations_path': 'migrations',
        'encoding': 'UTF8',
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
        self.database.initialize(connect(self.options['connection']))

        # Fix encoding for pg
        if isinstance(self.database.obj, pw.PostgresqlDatabase):
            self.database.obj.get_conn().set_client_encoding(self.options.encoding)

        self.threadpool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.options['max_connections'])

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

    @asyncio.coroutine
    def middleware_factory(self, app, handler):
        """ Control connection to database. """
        @asyncio.coroutine
        def middleware(request):
            if self.options['connection'].startswith('sqlite'):
                return (yield from handler(request))

            self.database.connect()
            response = yield from handler(request)
            if not self.database.is_closed():
                self.database.close()
            return response

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
