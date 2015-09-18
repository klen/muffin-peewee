"""Custom fields."""
import ujson
from cached_property import cached_property
from peewee import Field, PostgresqlDatabase, Proxy


try:
    from playhouse.postgres_ext import Json, JsonLookup
    PostgresqlDatabase.register_fields({'json': 'json'})
except:
    Json = JsonLookup = None


class JSONField(Field):

    """Implement JSON field."""

    def __init__(self, dumps=None, loads=None, *args, **kwargs):
        """Initialize the serializer."""
        self.dumps = dumps or ujson.dumps
        self.loads = loads or ujson.loads
        super(JSONField, self).__init__(*args, **kwargs)

    @cached_property
    def db_field(self):
        """Return database field type."""
        database = self.get_database()
        if isinstance(database, Proxy):
            database = database.obj
        if Json and isinstance(database, PostgresqlDatabase):
            return 'json'
        return 'text'

    def db_value(self, value):
        """Convert python value to database."""
        if self.db_field == 'text':
            return self.dumps(value)

        if not isinstance(value, Json):
            return Json(value, dumps=self.dumps)

        return value

    def coerce(self, value):
        """Parse value from database."""
        if self.db_field == 'text':
            return self.loads(value)
        return value

    def __getitem__(self, value):
        """Lookup item in database."""
        return JsonLookup(self, [value])
