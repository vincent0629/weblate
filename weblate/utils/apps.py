#
# Copyright © 2012–2023 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <https://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from django.apps import AppConfig
from django.core.checks import register
from django.db.models import CharField, TextField
from django.db.models.lookups import IExact

from weblate.utils.checks import (
    check_cache,
    check_celery,
    check_data_writable,
    check_database,
    check_diskspace,
    check_encoding,
    check_errors,
    check_mail_connection,
    check_perms,
    check_settings,
    check_site,
    check_version,
)
from weblate.utils.db import using_postgresql
from weblate.utils.errors import init_error_collection

from .db import (
    MySQLSearchLookup,
    PostgreSQLILikeLookup,
    PostgreSQLSearchLookup,
    PostgreSQLSubstringLookup,
)


class UtilsConfig(AppConfig):
    name = "weblate.utils"
    label = "utils"
    verbose_name = "Utils"

    def ready(self):
        super().ready()
        register(check_data_writable)
        register(check_mail_connection, deploy=True)
        register(check_celery, deploy=True)
        register(check_cache, deploy=True)
        register(check_settings, deploy=True)
        register(check_database, deploy=True)
        register(check_site)
        register(check_perms, deploy=True)
        register(check_errors, deploy=True)
        register(check_version, deploy=True)
        register(check_encoding)
        register(check_diskspace, deploy=True)

        init_error_collection()

        if using_postgresql():
            lookups = (
                (PostgreSQLILikeLookup,),
                (PostgreSQLSearchLookup,),
                (PostgreSQLSubstringLookup,),
            )
        else:
            lookups = (
                (IExact, "ilike"),
                (MySQLSearchLookup,),
                (MySQLSearchLookup, "substring"),
            )

        for lookup in lookups:
            CharField.register_lookup(*lookup)
            TextField.register_lookup(*lookup)
