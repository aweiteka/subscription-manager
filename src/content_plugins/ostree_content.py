#
# Copyright (c) 2013 Red Hat, Inc.
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

from subscription_manager import api
requires_api_version = "1.1"

# install our helper modules here
from subscription_manager.plugin import ostree
from subscription_manager.plugin.ostree import action_invoker


class OstreeContentPlugin(api.base_plugin.SubManPlugin):
    """Plugin for adding ostree content action to subscription-manager"""
    name = "ostree_content"

    def content_plugin_search_hook(self, conduit):
        """'content_plugin_search' hook to add ostree content action

        Args:
            conduit: A ContentActionPluginConduit
        """
        conduit.log.info("ostree_content content_plugin_search called")
        conduit.log.debug("ostree module: %s" % ostree)
        conduit.log.debug("dir(ostree): %s" % dir(ostree))
        conduit.content_action_class_list.append(action_invoker.OstreeContentActionInvoker)