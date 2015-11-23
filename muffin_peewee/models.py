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


class Signal:

    """Simplest signals implementation.

    ::
        @Model.post_save
        def example(instance, created=False):
            pass

    """

    __slots__ = 'receivers'

    def __init__(self):
        """Initialize the signal."""
        self.receivers = []

    def connect(self, receiver):
        """Append receiver."""
        if not callable(receiver):
            raise ValueError('Invalid receiver: %s' % receiver)
        self.receivers.append(receiver)

    def __call__(self, receiver):
        """Support decorators.."""
        self.connect(receiver)
        return receiver

    def disconnect(self, receiver):
        """Remove receiver."""
        try:
            self.receivers.remove(receiver)
        except ValueError:
            raise ValueError('Unknown receiver: %s' % receiver)

    def send(self, instance, *args, **kwargs):
        """Send signal."""
        for receiver in self.receivers:
            receiver(instance, *args, **kwargs)


class BaseSignalModel(pw.BaseModel):

    """Create signals."""

    def __new__(mcs, name, bases, attrs):
        """Create signals."""
        cls = super(BaseSignalModel, mcs).__new__(mcs, name, bases, attrs)
        cls.pre_save = Signal()
        cls.pre_delete = Signal()
        cls.post_delete = Signal()
        cls.post_save = Signal()
        return cls


class Model(pw.Model, metaclass=BaseSignalModel):

    """Upgraded Model class. Supports serialization, signals and model.pk attribute."""

    to_simple = to_simple

    @property
    def simple(self):
        """Serialize the model."""
        return self.to_simple()

    @property
    def pk(self):
        """Return primary key value."""
        return self._get_pk_value()

    def save(self, force_insert=False, **kwargs):
        """Send signals."""
        created = force_insert or not bool(self.pk)
        self.pre_save.send(self, created=created)
        super(Model, self).save(force_insert=force_insert, **kwargs)
        self.post_save.send(self, created=created)

    def delete_instance(self, *args, **kwargs):
        """Send signals."""
        self.pre_delete.send(self)
        super(Model, self).delete_instance(*args, **kwargs)
        self.post_delete.send(self)


class TModel(Model):

    """Store created time."""

    created = pw.DateTimeField(default=dt.datetime.utcnow)
