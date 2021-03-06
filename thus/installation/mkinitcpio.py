#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  mkinitcpio.py
#
#  This file was forked from Cnchi (graphical installer from Antergos)
#  Check it at https://github.com/antergos
#
#  Copyright 2013 Antergos (http://antergos.com/)
#  Copyright 2013 Manjaro (http://manjaro.org)
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

""" Module to setup and run mkinitcpio """

import logging
import os

from installation import chroot
from configobj import ConfigObj

conf_file = '/etc/thus.conf'
configuration = ConfigObj(conf_file)

def run(dest_dir, settings, mount_devices, blvm):
    """ Runs mkinitcpio """

    cpu = get_cpu()

    # Add lvm and encrypt hooks if necessary
    hooks = ["base", "udev", "autodetect", "modconf", "block", "keyboard", "keymap"]
    modules = []

    # It is important that the plymouth hook comes before any encrypt hook

    plymouth_bin = os.path.join(dest_dir, "usr/bin/plymouth")
    if os.path.exists(plymouth_bin):
        hooks.append("plymouth")

    # It is important that the encrypt hook comes before the filesystems hook
    # (in case you are using LVM on LUKS, the order should be: encrypt lvm2 filesystems)

    if settings.get("use_luks"):
        if os.path.exists(plymouth_bin):
            hooks.append("plymouth-encrypt")
        else:
            hooks.append("encrypt")

        modules.extend(["dm_mod", "dm_crypt", "ext4"])

        arch = os.uname()[-1]
        if arch == 'x86_64':
            modules.extend(["aes_x86_64"])
        else:
            modules.extend(["aes_i586"])

        modules.extend(["sha256", "sha512"])

    if settings.get("f2fs"):
        modules.append("f2fs")

    if blvm or settings.get("use_lvm"):
        hooks.append("lvm2")

    if "swap" in mount_devices:
        hooks.append("resume")

    hooks.append("filesystems")

    if settings.get('btrfs') and cpu is not 'genuineintel':
        modules.append('crc32c')
    elif settings.get('btrfs') and cpu is 'genuineintel':
        modules.append('crc32c-intel')
    else:
        hooks.append("fsck")

    set_hooks_and_modules(dest_dir, hooks, modules)

    # Run mkinitcpio on the target system
    # Fix for bsdcpio error. See: http://forum.antergos.com/viewtopic.php?f=5&t=1378&start=20#p5450
    locale = settings.get('locale')
    kernel = configuration['install']['KERNEL']
    cmd = ['sh', '-c', 'LANG={0} /usr/bin/mkinitcpio -p {1}'.format(locale,kernel)]
    chroot.run(cmd, dest_dir)


def set_hooks_and_modules(dest_dir, hooks, modules):
    """ Set up mkinitcpio.conf """
    logging.debug(_("Setting hooks and modules in mkinitcpio.conf"))
    logging.debug('HOOKS="{0}"'.format(' '.join(hooks)))
    logging.debug('MODULES="{0}"'.format(' '.join(modules)))

    with open("/etc/mkinitcpio.conf") as mkinitcpio_file:
        mklins = [x.strip() for x in mkinitcpio_file.readlines()]

    for i in range(len(mklins)):
        if mklins[i].startswith("HOOKS"):
            mklins[i] = 'HOOKS="{0}"'.format(' '.join(hooks))
        elif mklins[i].startswith("MODULES"):
            mklins[i] = 'MODULES="{0}"'.format(' '.join(modules))

    path = os.path.join(dest_dir, "etc/mkinitcpio.conf")
    with open(path, "w") as mkinitcpio_file:
        mkinitcpio_file.write("\n".join(mklins) + "\n")


def get_cpu():
    """ Gets CPU string definition """
    with open("/proc/cpuinfo") as proc_file:
        lines = proc_file.readlines()

    for line in lines:
        if "vendor_id" in line:
            return line.split(":")[1].replace(" ", "").lower()
    return ""
