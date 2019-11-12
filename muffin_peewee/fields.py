"""Custom fields."""
from cached_property import cached_property
from peewee import Field, PostgresqlDatabase, Proxy
from muffin.utils import json


try:
    from playhouse.postgres_ext import Json, JsonLookup
    PostgresqlDatabase.field_types['JSON'] = 'JSON'
except:  # noqa
    Json = JsonLookup = None


class JSONField(Field):

    """Implement JSON field."""

    def __init__(self, dumps=None, loads=None, *args, **kwargs):
        """Initialize the serializer."""
        self.dumps = dumps or json.dumps
        self.loads = loads or json.loads
        super(JSONField, self).__init__(*args, **kwargs)

    @cached_property
    def field_type(self):
        """Return database field type."""
        if not self.model:
            return 'JSON'
        database = self.model._meta.database
        if isinstance(database, Proxy):
            database = database.obj
        if Json and isinstance(database, PostgresqlDatabase):
            return 'JSON'
        return 'TEXT'

    def db_value(self, value):
        """Convert python value to database."""
        if self.field_type == 'TEXT':
            return self.dumps(value)

        if not isinstance(value, Json):
            return Json(value, dumps=self.dumps)

        return value

    def python_value(self, value):
        """Parse value from database."""
        if self.field_type == 'TEXT' and isinstance(value, str):
            return self.loads(value)
        return value

    def __getitem__(self, value):
        """Lookup item in database."""
        return JsonLookup(self, [value])
