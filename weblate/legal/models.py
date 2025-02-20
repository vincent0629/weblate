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

from datetime import date

from appconf import AppConf
from django.conf import settings
from django.db import models

from weblate.accounts.models import AuditLog
from weblate.utils.request import get_ip_address, get_user_agent


class WeblateLegalConf(AppConf):
    # Current TOS date
    LEGAL_TOS_DATE = date(2017, 7, 2)

    class Meta:
        prefix = ""


class Agreement(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, unique=True, on_delete=models.deletion.CASCADE
    )
    tos = models.DateField(default=date(1970, 1, 1))
    address = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=200, default="")
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TOS agreement"
        verbose_name_plural = "TOS agreements"

    def __str__(self):
        return f"{self.user.username}:{self.tos}"

    def is_current(self):
        return self.tos == settings.LEGAL_TOS_DATE

    def make_current(self, request):
        if not self.is_current():
            AuditLog.objects.create(
                self.user, request, "tos", date=settings.LEGAL_TOS_DATE.isoformat()
            )
            self.tos = settings.LEGAL_TOS_DATE
            self.address = get_ip_address(request)
            self.user_agent = get_user_agent(request)
            self.save()
