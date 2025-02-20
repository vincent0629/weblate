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

import hashlib
import os
import stat
import subprocess
from base64 import b64decode, b64encode

from django.conf import settings
from django.core.management.utils import find_command
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from weblate.trans.util import get_clean_env
from weblate.utils import messages
from weblate.utils.data import data_dir
from weblate.utils.hash import calculate_checksum

# SSH key files
KNOWN_HOSTS = "known_hosts"
CONFIG = "config"
RSA_KEY = "id_rsa"
RSA_KEY_PUB = "id_rsa.pub"


def ssh_file(filename):
    """Generate full path to SSH configuration file."""
    return os.path.join(data_dir("ssh"), filename)


def is_key_line(key):
    """Check whether this line looks like a valid known_hosts line."""
    if not key:
        return False
    # Comment
    if key[0] == "#":
        return False
    # Special entry like @cert-authority
    if key[0] == "@":
        return False
    return (
        " ssh-rsa " in key or " ecdsa-sha2-nistp256 " in key or " ssh-ed25519 " in key
    )


def parse_hosts_line(line):
    """Parse single hosts line into tuple host, key fingerprint."""
    host, keytype, key = line.strip().split(None, 3)[:3]
    digest = hashlib.sha256(b64decode(key)).digest()
    fingerprint = b64encode(digest).rstrip(b"=").decode()
    if host.startswith("|1|"):
        # Translators: placeholder SSH hashed hostname
        host = _("[hostname hashed]")
    return host, keytype, fingerprint


def get_host_keys():
    """Return list of host keys."""
    try:
        result = []
        with open(ssh_file(KNOWN_HOSTS)) as handle:
            for line in handle:
                line = line.strip()
                if is_key_line(line):
                    result.append(parse_hosts_line(line))
    except OSError:
        return []

    return result


def get_key_data():
    """Parse host key and returns it."""
    # Read key data if it exists
    if os.path.exists(ssh_file(RSA_KEY_PUB)):
        with open(ssh_file(RSA_KEY_PUB)) as handle:
            key_data = handle.read()
        key_type, key_fingerprint, key_id = key_data.strip().split(None, 2)
        return {
            "key": key_data,
            "type": key_type,
            "fingerprint": key_fingerprint,
            "id": key_id,
        }
    return None


def ensure_ssh_key():
    """Ensures SSH key is existing."""
    ssh_key = get_key_data()
    if not ssh_key:
        generate_ssh_key(None)
        ssh_key = get_key_data()
    return ssh_key


def generate_ssh_key(request):
    """Generate SSH key."""
    keyfile = ssh_file(RSA_KEY)
    pubkeyfile = ssh_file(RSA_KEY_PUB)
    try:
        # Actually generate the key
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-b",
                "4096",
                "-N",
                "",
                "-C",
                settings.SITE_TITLE,
                "-t",
                "rsa",
                "-f",
                keyfile,
            ],
            text=True,
            check=True,
            capture_output=True,
            env=get_clean_env(),
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        messages.error(
            request, _("Failed to generate key: %s") % getattr(exc, "output", str(exc))
        )
        return

    # Fix key permissions
    os.chmod(keyfile, stat.S_IWUSR | stat.S_IRUSR)
    os.chmod(pubkeyfile, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    messages.success(request, _("Created new SSH key."))


def add_host_key(request, host, port=""):
    """Add host key for a host."""
    if not host:
        messages.error(request, _("Invalid host name given!"))
    else:
        cmdline = ["ssh-keyscan"]
        if port:
            cmdline.extend(["-p", str(port)])
        cmdline.append(host)
        try:
            result = subprocess.run(
                cmdline,
                env=get_clean_env(),
                check=True,
                text=True,
                capture_output=True,
            )
            keys = set()
            for key in result.stdout.splitlines():
                key = key.strip()
                if not is_key_line(key):
                    continue
                keys.add(key)
                host, keytype, fingerprint = parse_hosts_line(key)
                messages.warning(
                    request,
                    _(
                        "Added host key for %(host)s with fingerprint "
                        "%(fingerprint)s (%(keytype)s), "
                        "please verify that it is correct."
                    )
                    % {"host": host, "fingerprint": fingerprint, "keytype": keytype},
                )
            if keys:
                known_hosts_file = ssh_file(KNOWN_HOSTS)
                # Remove existing key entries
                if os.path.exists(known_hosts_file):
                    with open(known_hosts_file) as handle:
                        for line in handle:
                            keys.discard(line.strip())
                # Write any new keys
                if keys:
                    with open(known_hosts_file, "a") as handle:
                        for key in keys:
                            handle.write(key)
                            handle.write("\n")
            else:
                messages.error(request, _("Failed to fetch public key for a host!"))
        except subprocess.CalledProcessError as exc:
            messages.error(
                request, _("Failed to get host key: %s") % exc.stderr or exc.stdout
            )
        except OSError as exc:
            messages.error(request, _("Failed to get host key: %s") % str(exc))


GITHUB_RSA_KEY = (
    "AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7"
    "PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQq"
    "ZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG"
    "6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3J"
    "EAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ=="
)


def cleanup_host_keys(*args, **kwargs):
    known_hosts_file = ssh_file(KNOWN_HOSTS)
    if not os.path.exists(known_hosts_file):
        return
    logger = kwargs.get("logger", print)  # noqa: T202
    keys = []
    with open(known_hosts_file) as handle:
        for line in handle:
            # Ignore IP address based RSA keys for GitHub, these
            # are duplicate to hostname based and cause problems on
            # migration to ECDSA.
            # See https://github.com/WeblateOrg/weblate/issues/6830
            if line[0].isdigit() and GITHUB_RSA_KEY in line:
                logger(f"Removing deprecated RSA key for GitHub: {line.strip()}")
                continue

            # Avoid duplicates
            if line in keys:
                logger(f"Skipping duplicate key: {line.strip()}")
                continue

            keys.append(line)

    with open(known_hosts_file, "w") as handle:
        handle.writelines(keys)


def can_generate_key():
    """Check whether we can generate key."""
    return find_command("ssh-keygen") is not None


SSH_WRAPPER_TEMPLATE = r"""#!/bin/sh
exec {command} \
    -o "UserKnownHostsFile={known_hosts}" \
    -o "IdentityFile={identity}" \
    -o StrictHostKeyChecking=yes \
    -o HashKnownHosts=no \
    -o UpdateHostKeys=yes \
    -F {config_file} \
    {extra_args} \
    "$@"
"""


class SSHWrapper:
    # Custom ssh wrapper
    # - use custom location for known hosts and key
    # - do not hash it
    # - strict hosk key checking
    # - force not using system configuration (to avoid evil things as SendEnv)

    @cached_property
    def digest(self):
        return calculate_checksum(self.get_content())

    @property
    def path(self):
        """Calculates unique wrapper path.

        It is based on template and DATA_DIR settings.
        """
        return ssh_file(f"bin-{self.digest}")

    def get_content(self, command="ssh"):
        return SSH_WRAPPER_TEMPLATE.format(
            command=command,
            known_hosts=ssh_file(KNOWN_HOSTS),
            config_file=ssh_file(CONFIG),
            identity=ssh_file(RSA_KEY),
            extra_args=settings.SSH_EXTRA_ARGS,
        )

    @property
    def filename(self):
        """Calculates unique wrapper filename."""
        return os.path.join(self.path, "ssh")

    def create(self):
        """Create wrapper for SSH to pass custom known hosts and key."""
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        if not os.path.exists(ssh_file(CONFIG)):
            try:
                with open(ssh_file(CONFIG), "x") as handle:
                    handle.write(
                        "# SSH configuration for customising SSH client in Weblate"
                    )
            except OSError:
                pass

        for command in ("ssh", "scp"):
            filename = os.path.join(self.path, command)

            if os.path.exists(filename):
                continue

            with open(filename, "w") as handle:
                handle.write(self.get_content(find_command(command)))

            os.chmod(filename, 0o755)  # nosec


SSH_WRAPPER = SSHWrapper()
