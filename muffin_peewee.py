"""Support Peewee ORM for Muffin framework."""

__version__ = "1.5.1"
__project__ = "muffin-peewee"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"

from aiopeewee import db_url, DatabaseAsync
from muffin.plugin import BasePlugin
from functools import cached_property
import peewee as pw
import json
from peewee_migrate import Router


try:
    from playhouse.postgres_ext import Json, JsonLookup
except ImportError:
    Json = JsonLookup = None


__all__ = 'Plugin', 'JSONField'


class Plugin(BasePlugin):

    """Muffin Peewee Plugin."""

    name = "peewee"
    defaults = {

        # Connection params
        'connection': 'sqlite:///db.sqlite',
        'connection_params': {},

        # Manage connections automatically
        'manage_connections': True,

        # Setup migration engine
        'migrations_enabled': True,
        'migrations_path': 'migrations',
    }

    def __init__(self, app=None, **options):
        """Initialize the plugin."""
        self.database = pw.Proxy()
        self.models = {}
        self.router = None
        super(Plugin, self).__init__(app, **options)

    def setup(self, app, **options):
        """Init the plugin."""
        super().setup(app, **options)
        self.database.initialize(db_url.connect(self.cfg.connection, **self.cfg.connection_params))

        if self.cfg.migrations_enabled:
            self.router = Router(self.database, migrate_dir=self.cfg.migrations_path)

            # Register migration commands
            @app.manage
            def pw_migrate(name: str = None, fake: bool = False):
                """Run application's migrations.

                :param name: Choose a migration' name
                :param fake: Run as fake. Update migration history and don't touch the database
                """
                self.router.run(name, fake=fake)

            @app.manage
            def pw_create(name: str = 'auto', auto: bool = False):
                """Create a migration.

                :param name: Set name of migration [auto]
                :param auto: Track changes and setup migrations automatically
                """
                if auto:
                    auto = list(self.models.values())
                self.router.create(name, auto)

            @app.manage
            def pw_rollback(name: str = None):
                """Rollback a migration.

                :param name: Migration name (actually it always should be a last one)
                """
                self.router.rollback(name)

            @app.manage
            def pw_list():
                """List migrations."""
                self.router.logger.info('Migrations are done:')
                self.router.logger.info('\n'.join(self.router.done))
                self.router.logger.info('')
                self.router.logger.info('Migrations are undone:')
                self.router.logger.info('\n'.join(self.router.diff))

        if not isinstance(self.database.obj, DatabaseAsync):
            return

        if self.cfg.manage_connections:
            self.app.middleware(self.__middleware__)

    def __getattr__(self, name):
        """Proxy attrs to self database."""
        return getattr(self.database.obj, name)

    async def __middleware__(self, handler, request, receive, send):
        """Manage connections."""
        await self.database.connect_async()

        try:
            response = await handler(request, receive, send)
            self.database.commit()
            return response

        except pw.DatabaseError:
            self.database.rollback()
            raise

        finally:
            self.database.close()

    async def __aenter__(self):
        """Connect async and enter the database context."""
        await self.database.connect_async()
        self.database.obj.__enter__()

    async def __aexit__(self, *args):
        """Exit from the database context."""
        self.database.obj.__exit__(*args)

    def shutdown(self):
        """Close all connections."""
        self.database.close_all()

    def register(self, model):
        """Register a model with the plugin."""
        self.models[model._meta.table_name] = model
        model._meta.database = self.database
        return model

    async def conftest(self):
        """Configure pytest tests."""
        for model in self.models.values():
            model.create_table()


class JSONField(pw.Field):

    """Implement JSON field."""

    unpack = False

    def __init__(self, json_dumps=None, json_loads=None, *args, **kwargs):
        """Initialize the serializer."""
        self._json_dumps = json_dumps or json.dumps
        self._json_loads = json_loads or json.loads
        super(JSONField, self).__init__(*args, **kwargs)

    def __getitem__(self, value):
        """Lookup item in database."""
        return JsonLookup(self, [value])

    @cached_property
    def field_type(self):
        """Return database field type."""
        database = self.model._meta.database
        if isinstance(database, pw.Proxy):
            database = database.obj
        if Json and isinstance(database, pw.PostgresqlDatabase):
            return 'json'
        return 'text'

    def python_value(self, value):
        """Deserialize value from DB."""
        if value is not None and self.field_type == 'text':
            try:
                return self._json_loads(value)
            except (TypeError, ValueError):
                pass

        return value

    def db_value(self, value):
        """Convert python value to database."""
        if value is None:
            return value

        if self.field_type == 'text':
            return self._json_dumps(value)

        if not isinstance(value, Json):
            return pw.Cast(self.dumps(value), 'json')

        return value

    def coerce(self, value):
        """Parse value from database."""
        if self.db_field == 'text' and isinstance(value, str):
            return self.loads(value)
        return value
