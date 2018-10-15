"""Models' utils."""
import datetime as dt

import peewee as pw
from playhouse.signals import Model as SignalModel, \
    pre_save, post_save, pre_delete, post_delete, pre_init


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
        """Get string representation."""
        return ", ".join(self._reversed.keys())

    def __repr__(self):
        """Python representation."""
        return "<Choices: %s>" % self


class Model(SignalModel):

    """Upgraded Model class. Supports signals and model.pk attribute."""

    pre_save = pre_save
    post_save = post_save
    pre_delete = pre_delete
    post_delete = post_delete
    pre_init = pre_init

    @property
    def pk(self):
        """Return primary key value."""
        return self._pk


class TModel(Model):

    """Store created time."""

    created = pw.DateTimeField(default=dt.datetime.utcnow)
