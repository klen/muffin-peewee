import datetime

import peewee

from example import db


# Register a model
@db.register
class DataItem(peewee.Model):
    created = peewee.DateTimeField(default=datetime.datetime.utcnow)
    content = peewee.CharField()
