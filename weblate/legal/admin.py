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

from weblate.wladmin.models import WeblateModelAdmin


class AgreementAdmin(WeblateModelAdmin):
    list_display = ["user", "tos", "timestamp", "address", "user_agent"]
    search_fields = ["user__username"]
    list_filter = ["tos"]
    date_hierarchy = "timestamp"
    ordering = ["user__username"]
