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

from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy

from weblate.checks.flags import Flags
from weblate.utils.colors import COLOR_CHOICES

TRANSLATION_LABELS = {"Automatically translated"}


class Label(models.Model):
    project = models.ForeignKey("Project", on_delete=models.deletion.CASCADE)
    name = models.CharField(verbose_name=gettext_lazy("Label name"), max_length=190)
    color = models.CharField(
        verbose_name=gettext_lazy("Color"),
        max_length=30,
        choices=COLOR_CHOICES,
        blank=False,
        default=None,
    )

    class Meta:
        app_label = "trans"
        unique_together = [("project", "name")]
        verbose_name = "label"
        verbose_name_plural = "label"

    def __str__(self):
        return format_html(
            '<span class="label label-{}">{}</span>', self.color, self.name
        )

    @property
    def filter_name(self):
        return f"label:{Flags.format_value(self.name)}"
