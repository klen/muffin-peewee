import datetime as dt

import peewee as pw
from playhouse.shortcuts import model_to_dict


def to_fields(model, values):
    """ Convert model field's names to model's fields.

    If field name in values the function will convert it to field.

    """
    if not values:
        return values

    values = set(values)
    return {field for field in model._meta.fields.values()
            if field.name in values or field in values}


def to_simple(model, **kwargs):
    """ Setialize a model to dictionary. """
    meta = model._meta
    kwargs.setdefault('recurse', getattr(meta, 'recurse', False))
    kwargs.setdefault('only', getattr(meta, 'only', None))
    kwargs.setdefault('exclude', getattr(meta, 'exclude', None))
    kwargs.setdefault('backrefs', getattr(meta, 'backrefs', False))
    kwargs['exclude'] = to_fields(model, kwargs['exclude'])
    kwargs['only'] = to_fields(model, kwargs['only'])
    return model_to_dict(model, **kwargs)


class Model(pw.Model):

    """ Upgraded Model class. Supports serialization and model.pk attribute. """

    to_simple = to_simple

    @property
    def simple(self):
        return self.to_simple()

    @property
    def pk(self):
        return self._get_pk_value()


class TModel(Model):

    """ Store created time. """

    created = pw.DateTimeField(default=dt.datetime.utcnow)
