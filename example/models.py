import datetime

import peewee

from example import app


# Register a model
@app.ps.peewee.register
class DataItem(peewee.Model):
    created = peewee.DateTimeField(default=datetime.datetime.utcnow)
    content = peewee.CharField()
