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

from django.conf import settings

from .base import MachineTranslation
from .forms import MyMemoryMachineryForm


class MyMemoryTranslation(MachineTranslation):
    """MyMemory machine translation support."""

    name = "MyMemory"
    do_cleanup = False
    settings_form = MyMemoryMachineryForm

    @staticmethod
    def migrate_settings():
        return {
            "email": settings.MT_MYMEMORY_EMAIL,
            "username": settings.MT_MYMEMORY_USER,
            "key": settings.MT_MYMEMORY_KEY,
        }

    def map_language_code(self, code):
        """Convert language to service specific code."""
        return super().map_language_code(code).replace("_", "-")

    def is_supported(self, source, language):
        """Check whether given language combination is supported."""
        return (
            self.lang_supported(source)
            and self.lang_supported(language)
            and source != language
        )

    @staticmethod
    def lang_supported(language):
        """Almost any language without modifiers is supported."""
        if language in ("ia", "tt", "ug"):
            return False
        return "@" not in language

    def format_match(self, match):
        """Reformat match to (translation, quality) tuple."""
        result = {
            "text": match["translation"],
            "quality": int(100 * match["match"]),
            "service": self.name,
            "source": match["segment"],
        }

        if match["last-updated-by"]:
            result["origin"] = match["last-updated-by"]

        if match["reference"]:
            result["origin_detail"] = match["reference"]

        return result

    def download_translations(
        self,
        source,
        language,
        text: str,
        unit,
        user,
        search: bool,
        threshold: int = 75,
    ):
        """Download list of possible translations from MyMemory."""
        args = {
            "q": text.split(". ")[0][:500],
            "langpair": f"{source}|{language}",
        }
        if self.settings["email"]:
            args["de"] = self.settings["email"]
        if self.settings["username"]:
            args["user"] = self.settings["username"]
        if self.settings["key"]:
            args["key"] = self.settings["key"]

        response = self.request_status(
            "get", "https://mymemory.translated.net/api/get", params=args
        )
        for match in response["matches"]:
            result = self.format_match(match)
            if result["quality"] > threshold:
                yield result
