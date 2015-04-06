import datetime as dt

import peewee as pw
from playhouse.shortcuts import model_to_dict


class Model(pw.Model):

    """ Upgraded Model class. Supports serialization and pk key. """

    def to_simple(self, recurse=False, exclude=None, **kwargs):
        exclude = exclude or getattr(self._meta, 'exclude', None)
        if exclude:
            exclude = {field for field in self._meta.fields.values() if field.name in exclude}
        return model_to_dict(self, recurse=recurse, exclude=exclude, **kwargs)

    @property
    def simple(self):
        return self.to_simple()

    @property
    def pk(self):
        return self._get_pk_value()


class TModel(Model):

    """ Store created time. """

    created = pw.DateTimeField(default=dt.datetime.utcnow)
