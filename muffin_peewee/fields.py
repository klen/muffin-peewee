"""Custom fields/properties."""

import typing as t
import json

import peewee as pw

try:
    from functools import cached_property  # type: ignore
except ImportError:
    from cached_property import cached_property  # type: ignore # XXX: Python 3.7

try:
    from playhouse.postgres_ext import Json, JsonLookup
except ImportError:
    Json = JsonLookup = None


class JSONField(pw.Field):

    """Implement JSON field."""

    unpack = False

    def __init__(
            self, json_dumps: t.Callable = None, json_loads: t.Callable = None, *args, **kwargs):
        """Initialize the serializer."""
        self._json_dumps = json_dumps or json.dumps
        self._json_loads = json_loads or json.loads
        super(JSONField, self).__init__(*args, **kwargs)

    def __getitem__(self, value) -> JsonLookup:
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
            return pw.Cast(self._json_dumps(value), 'json')

        return value


class Choices:

    """Model's choices helper."""

    __slots__ = '_choices', '_map', '_rmap'

    def __init__(self, choices, *args):
        """Parse provided choices."""
        if isinstance(choices, dict):
            choices = [(n, v) for v, n in choices.items()]

        elif args:
            choices = [choices, *args]

        self._choices = [
            (choice, choice) if isinstance(choice, str) else choice
            for choice in choices
        ]
        self._map = dict([(n, v) for v, n in self._choices])
        self._rmap = dict(self._choices)

    def __iter__(self):
        """Iterate self."""
        return iter(self._choices)

    def __getattr__(self, name, default=None):
        """Get choice value by name."""
        return self._map.get(name, default)

    def __getitem__(self, name):
        """Get value by name."""
        return self._map[name]

    def __call__(self, value):
        """Get name by value."""
        return self._rmap[value]

    def __deepcopy__(self, memo):
        """Deep copy self."""
        result = Choices(self._map.copy())
        memo[id(self)] = result
        return result
