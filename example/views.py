import random
import string

from example import app, muffin, models


@app.register('/')
def list(request):
    objects = models.DataItem.select()
    template = """
        <html>
            <h3>Items: </h3>
            <a href="/generate"> Generate new Item </a>&nbsp;&nbsp;&nbsp;
            <a href="/clean"> Clean everything </a>
            <ul>%s</ul>
        </html>
    """ % "".join("<li>%s&nbsp;|&nbsp;%s</li>" % (d.created, d.content) for d in objects)
    return template


@app.register('/generate')
def generate(request):
    """ Create a new DataItem. """
    models.DataItem.create(
        content=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
    )
    return muffin.HTTPFound('/')


@app.register('/clean')
def clean(request):
    """ Create a new DataItem. """
    models.DataItem.delete().execute()
    return muffin.HTTPFound('/')
