"""Debugtoolbar itegration for Muffin-Peewee."""

import logging
import jinja2
import datetime as dt

from muffin_debugtoolbar.panels import DebugPanel
from muffin_debugtoolbar.utils import LoggingTrackingHandler


LOGGER = logging.getLogger('peewee')


class DebugPanel(DebugPanel):

    """Provide information about executed SQL queries."""

    name = 'Peewee queries'
    template = jinja2.Template("""
        <table class="table table-striped table-condensed">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Query</th>
                </tr>
            </thead>
            <tbody>
                {% for record in records %}
                    <tr>
                        <td>{{ record['time'] }}</td>
                        <td>{{ record['message'] }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    """)

    def __init__(self, app, request=None):
        """Initialize the panel."""
        super(DebugPanel, self).__init__(app, request)
        LOGGER.setLevel(logging.DEBUG)
        self.handler = LoggingTrackingHandler()

    def wrap_handler(self, handler, context_switcher):
        """Enable/Disable handler."""
        context_switcher.add_context_in(lambda: LOGGER.addHandler(self.handler))
        context_switcher.add_context_out(lambda: LOGGER.removeHandler(self.handler))

    @property
    def nav_title(self):
        """Get a navigation title."""
        return "%s (%s)" % (self.title, len(self.handler.records))

    @property
    def has_content(self):
        """Return true if records were logged."""
        return self.handler.records

    def render_vars(self):
        """Template variables."""
        return {
            'records': [
                {
                    'message': record.getMessage(),
                    'time': dt.datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                } for record in self.handler.records
            ]
        }
