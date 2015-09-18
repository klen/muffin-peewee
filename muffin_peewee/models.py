"""Models' utils."""
import datetime as dt

import peewee as pw
from playhouse.shortcuts import model_to_dict


def to_fields(model, values):
    """Convert model field's names to model's fields.

    If field name in values the function will convert it to field.

    """
    if not values:
        return values

    values = set(values)
    return {field for field in model._meta.fields.values()
            if field.name in values or field in values}


def to_simple(model, **kwargs):
    """Setialize a model to dictionary."""
    meta = model._meta
    kwargs.setdefault('recurse', getattr(meta, 'recurse', False))
    kwargs.setdefault('only', getattr(meta, 'only', None))
    kwargs.setdefault('exclude', getattr(meta, 'exclude', None))
    kwargs.setdefault('backrefs', getattr(meta, 'backrefs', False))
    kwargs['exclude'] = to_fields(model, kwargs['exclude'])
    kwargs['only'] = to_fields(model, kwargs['only'])
    return model_to_dict(model, **kwargs)


class Choices:

    """Model's choices helper."""

    def __init__(self, *choices):
        """Parse provided choices."""
        self._choices = []
        self._reversed = {}
        for choice in choices:
            if isinstance(choice, str):
                choice = (choice, choice)
            self._choices.append(choice)
            self._reversed[str(choice[1])] = choice[0]

    def __getattr__(self, name, default=None):
        """Get choice value by name."""
        return self._reversed.get(name, default)

    def __iter__(self):
        """Iterate self."""
        return iter(self._choices)

    def __str__(self):
        """String representation."""
        return ", ".join(self._reversed.keys())

    def __repr__(self):
        """Python representation."""
        return "<Choices: %s>" % self


class Model(pw.Model):

    """Upgraded Model class. Supports serialization and model.pk attribute."""

    to_simple = to_simple

    @property
    def simple(self):
        """Serialize the model."""
        return self.to_simple()

    @property
    def pk(self):
        """Return primary key value."""
        return self._get_pk_value()


class TModel(Model):

    """Store created time."""

    created = pw.DateTimeField(default=dt.datetime.utcnow)
