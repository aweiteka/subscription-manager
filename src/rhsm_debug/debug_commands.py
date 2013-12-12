#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import gettext
import os
import sys
import shutil
import logging
import tarfile
from datetime import datetime

import subscription_manager.injection as inj
import subscription_manager.managercli as managercli
from subscription_manager.managercli import CliCommand
from rhsm import ourjson as json
from rhsm.config import initConfig

_ = gettext.gettext

cfg = initConfig()

log = logging.getLogger('rhsm-app.' + __name__)

NOT_REGISTERED = _("This system is not yet registered. Try 'subscription-manager register --help' for more information.")

ASSEMBLE_DIR = '/var/spool/rhsm/debug'


class SystemCommand(CliCommand):

    def __init__(self, name="system",
                 shortdesc=_("Assemble system information as a tar file or directory"),
                 primary=True):
        CliCommand.__init__(self, name=name, shortdesc=shortdesc, primary=primary)

        self.parser.add_option("--destination", dest="destination",
                               default="/tmp", help=_("the destination location of the result"))
        # default is to build an archive, this skips the archive and clean up,
        # just leaving the directory of debug info for sosreport to report
        self.parser.add_option("--no-archive", action='store_false',
                               default=True, dest="archive",
                               help=_("data will be in an uncompressed directory"))

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] ") % self.name

    def _do_command(self):
        consumer = inj.require(inj.IDENTITY)
        if not consumer.is_valid():
            print NOT_REGISTERED
            sys.exit(-1)

        code = self._make_code()
        assemble_path = self._get_assemble_dir()
        content_path = os.path.join(assemble_path, code)
        tar_path = os.path.join(assemble_path, "tar")

        try:
            os.makedirs(content_path)

            owner = self.cp.getOwner(consumer.uuid)

            try:
                self._write_flat_file(content_path, "subscriptions.json",
                                      self.cp.getSubscriptionList(owner['key']))
            except Exception, e:
                log.warning("Server does not allow retrieval of subscriptions by owner.")

            self._write_flat_file(content_path, "consumer.json",
                                  self.cp.getConsumer(consumer.uuid))
            self._write_flat_file(content_path, "compliance.json",
                                  self.cp.getCompliance(consumer.uuid))
            self._write_flat_file(content_path, "entitlements.json",
                                  self.cp.getEntitlementList(consumer.uuid))
            self._write_flat_file(content_path, "pools.json",
                                  self.cp.getPoolsList(consumer.uuid, True, None, owner['key']))
            self._write_flat_file(content_path, "version.json",
                                  self._get_version_info())

            # FIXME: we need to anon proxy passwords?
            self._copy_directory('/etc/rhsm', content_path)
            self._copy_directory('/var/log/rhsm', content_path)
            self._copy_directory('/var/lib/rhsm', content_path)
            self._copy_directory(cfg.get('rhsm', 'productCertDir'), content_path)
            self._copy_directory(cfg.get('rhsm', 'entitlementCertDir'), content_path)
            self._copy_directory(cfg.get('rhsm', 'consumerCertDir'), content_path)

            # FIXME: this could still be in /tmp
            # FIXME: destination is user input from a trusted user, but it
            # could still be something dumb
            print "destination", self.options.destination
            if not os.path.exists(self.options.destination):
                os.makedirs(self.options.destination)

            # build an archive by default
            if self.options.archive:
                os.makedirs(tar_path)
                tar_file_path = os.path.join(tar_path, "tmp-system.tar")
                print "tar_path", tar_path, tar_file_path
                tf = tarfile.open(tar_file_path, "w:gz")
                # FIXME: full name
                tf.add(content_path, code)
                tf.close()
                final_path = os.path.join(self.options.destination, "system-debug-%s.tar.gz" % code)
                print "final_path", final_path

                # FIXME: move securely
                # FIXME: perms should be 0600, only root can read
                shutil.move(tar_file_path, final_path)
                print _("Wrote: %s") % final_path
            else:
                # FIXME: need to do this securely
                shutil.move(content_path, self.options.destination)

                print _("Wrote: %s/%s") % (self.options.destination, code)

        except Exception, e:
            managercli.handle_exception(_("Unable to create zip file of system information: %s") % e, e)
            sys.exit(-1)
        finally:
            if assemble_path and os.path.exists(assemble_path):
                shutil.rmtree(assemble_path, True)

    def _make_code(self):
        return datetime.now().strftime("%Y%m%d-%f")

    def _get_version_info(self):
        return {"server type": self.server_versions["server-type"],
                "subscription management server": self.server_versions["candlepin"],
                "subscription-manager": self.client_versions["subscription-manager"],
                "python-rhsm": self.client_versions["python-rhsm"]}

    def _write_flat_file(self, content_path, filename, content):
        path = os.path.join(content_path, filename)
        with open(path, "w+") as fo:
            fo.write(json.dumps(content, indent=4, sort_keys=True))

    def _copy_directory(self, src_path, dest_path):
        rel_path = src_path
        if os.path.isabs(src_path):
            rel_path = src_path[1:]
        shutil.copytree(src_path, os.path.join(dest_path, rel_path))

    def _get_assemble_dir(self):
        return ASSEMBLE_DIR
