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

from typing import Optional

from django.db import transaction

from weblate.machinery.base import get_machinery_language
from weblate.memory.models import Memory
from weblate.utils.celery import app
from weblate.utils.state import STATE_TRANSLATED


@app.task(trail=False)
def import_memory(project_id: int, component_id: Optional[int] = None):
    from weblate.trans.models import Project, Unit

    project = Project.objects.get(pk=project_id)

    components = project.component_set.all()
    if component_id:
        components = components.filter(id=component_id)

    for component in components.iterator():
        component.log_info("updating translation memory")
        with transaction.atomic():
            units = Unit.objects.filter(
                translation__component=component, state__gte=STATE_TRANSLATED
            ).exclude(target="")
            if not component.intermediate:
                units = units.exclude(
                    translation__language_id=component.source_language_id
                )
            for unit in units.prefetch_related("translation", "translation__language"):
                update_memory(None, unit, component, project)


@app.task(trail=False)
def handle_unit_translation_change(unit_id, user_id=None):
    from weblate.auth.models import User
    from weblate.trans.models import Unit

    user = None if user_id is None else User.objects.get(pk=user_id)
    unit = Unit.objects.select_related(
        "translation",
        "translation__language",
        "translation__component",
        "translation__component__source_language",
        "translation__component__project",
    ).get(pk=unit_id)
    update_memory(user, unit)


def update_memory(user, unit, component=None, project=None):
    component = component or unit.translation.component
    project = project or component.project
    params = {
        "source_language": get_machinery_language(component.source_language),
        "target_language": get_machinery_language(unit.translation.language),
        "source": unit.source,
        "target": unit.target,
        "origin": component.full_slug,
    }

    add_project = True
    add_shared = project.contribute_shared_tm
    add_user = user is not None

    # Check matching entries in memory
    for matching in Memory.objects.filter(from_file=False, **params):
        if (
            matching.user_id is None
            and matching.project_id == project.id
            and not matching.shared
        ):
            add_project = False
        elif (
            add_shared
            and matching.user_id is None
            and matching.project_id is None
            and matching.shared
        ):
            add_shared = False
        elif (
            add_user
            and matching.user_id == user.id
            and matching.project_id is None
            and not matching.shared
        ):
            add_user = False

    to_create = []

    if add_project:
        to_create.append(
            Memory(user=None, project=project, from_file=False, shared=False, **params)
        )
    if add_shared:
        to_create.append(
            Memory(user=None, project=None, from_file=False, shared=True, **params)
        )
    if add_user:
        to_create.append(
            Memory(user=user, project=None, from_file=False, shared=False, **params)
        )
    if to_create:
        Memory.objects.bulk_create(to_create)
