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

from weblate.auth.models import Group
from weblate.trans.tests.test_views import ViewTestCase


class TeamsTest(ViewTestCase):
    def make_superuser(self, superuser: bool = True):
        self.user.is_superuser = superuser
        self.user.save()

    def test_sitewide(self):
        group = Group.objects.create(name="Test group")
        edit_payload = {
            "name": "Other",
            "language_selection": "1",
            "project_selection": "1",
            "autogroup_set-TOTAL_FORMS": "0",
            "autogroup_set-INITIAL_FORMS": "0",
        }
        response = self.client.get(group.get_absolute_url())
        self.assertEqual(response.status_code, 403)

        # Edit not allowed
        response = self.client.post(group.get_absolute_url(), edit_payload)
        group.refresh_from_db()
        self.assertEqual(group.name, "Test group")

        self.make_superuser()
        response = self.client.get(group.get_absolute_url())
        self.assertContains(response, "id_autogroup_set-TOTAL_FORMS")

        response = self.client.post(group.get_absolute_url(), edit_payload)
        self.assertRedirects(response, group.get_absolute_url())
        group.refresh_from_db()
        self.assertEqual(group.name, "Other")

    def test_project(self):
        group = Group.objects.create(name="Test group", defining_project=self.project)

        edit_payload = {
            "name": "Other",
            "language_selection": "1",
            "autogroup_set-TOTAL_FORMS": "0",
            "autogroup_set-INITIAL_FORMS": "0",
        }
        response = self.client.get(group.get_absolute_url())
        self.assertEqual(response.status_code, 403)

        # Edit not allowed
        response = self.client.post(group.get_absolute_url(), edit_payload)
        group.refresh_from_db()
        self.assertEqual(group.name, "Test group")

        self.make_superuser()
        response = self.client.get(group.get_absolute_url())
        self.assertContains(response, "id_autogroup_set-TOTAL_FORMS")

        response = self.client.post(group.get_absolute_url(), edit_payload)
        self.assertRedirects(response, group.get_absolute_url())
        group.refresh_from_db()
        self.assertEqual(group.name, "Other")

    def test_add_users(self):
        group = Group.objects.create(name="Test group", defining_project=self.project)

        # Non-privileged
        self.client.post(
            group.get_absolute_url(), {"add_user": "1", "user": self.user.username}
        )
        self.assertEqual(group.user_set.count(), 0)
        self.assertEqual(group.admins.count(), 0)

        # Superuser
        self.make_superuser()
        self.client.post(
            group.get_absolute_url(), {"add_user": "1", "user": "x-invalid"}
        )
        self.assertEqual(group.user_set.count(), 0)
        self.assertEqual(group.admins.count(), 0)
        self.client.post(
            group.get_absolute_url(), {"add_user": "1", "user": self.user.username}
        )
        self.assertEqual(group.user_set.count(), 1)
        self.assertEqual(group.admins.count(), 0)

        self.client.post(
            group.get_absolute_url(),
            {"add_user": "1", "user": self.user.username, "make_admin": "1"},
        )
        self.assertEqual(group.user_set.count(), 1)
        self.assertEqual(group.admins.count(), 1)

        # Team admin
        self.make_superuser(False)
        self.client.post(
            group.get_absolute_url(),
            {"add_user": "1", "user": self.anotheruser.username},
        )
        self.assertEqual(group.user_set.count(), 2)
        self.assertEqual(group.admins.count(), 1)

        self.client.post(
            group.get_absolute_url(),
            {"add_user": "1", "user": self.anotheruser.username, "make_admin": "1"},
        )
        self.assertEqual(group.user_set.count(), 2)
        self.assertEqual(group.admins.count(), 2)

        self.client.post(
            group.get_absolute_url(),
            {"add_user": "1", "user": self.anotheruser.username},
        )
        self.assertEqual(group.user_set.count(), 2)
        self.assertEqual(group.admins.count(), 1)
