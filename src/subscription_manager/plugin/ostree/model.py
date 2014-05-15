import copy
import logging
import re
import sys

from subscription_manager.plugin.ostree import repo_file

OSTREE_REPO_CONFIG_PATH = "/ostree/repo/config"

REMOTE_SECTION_MATCH = r"remote\s+\"(?P<remote_name>.+)\""

log = logging.getLogger("rhsm-app." + __name__)


class OstreeContentError(Exception):
    pass


class RemoteSectionNameParseError(OstreeContentError):
    pass


# FIXME: remove property stuff, dont inherit from dict, remove hash stuff
#        it's clever but weird and unneeded, but commit so tests work
class OstreeRemote(object):
    """Represent a ostree repo remote.

    A repo remote is one of the the '[remote "ostree-awesomeos-8"]' section in
    ostree repo config (/ostree/repo/config by default).
    """

    items_to_data = {'gpg-verify': 'gpg_verify'}

    def __init__(self):
        self.data = {}

    # for remote_key in remote iterates over the config items
    def __iter__(self):
        return iter(self.data)

    @property
    def url(self):
        return self.data.get('url')

    @url.setter
    def url(self, value):
        self.data['url'] = value

    @property
    def gpg_verify(self):
        return self.data.get('gpg_verify')

    @gpg_verify.setter
    def gpg_verify(self, value):
        self.data['gpg_verify'] = value

    @property
    def name(self):
        return self.data.get('name')

    @name.setter
    def name(self, value):
        self.data['name'] = value

    @classmethod
    def from_config_section(cls, section, items):
        """Create a OstreeRemote object from a repo config section name and map of items.

        'section' is the name of the remote section in the repo config file. For
          ex: 'remote "ostree-awesomeos-8"'
        'items' is a map of items corresponding to config items for 'section'. Extra
          items we don't understand are ignored. Expect at least 'url'.

        Note: 'gpg-verify' is one of the default items, but 'gpg-verify' is not
              a valid python attribute name, so a key of 'gpg-verify' is used to
              update the OstreeRemote.gpg_verify property.
        """
        remote = cls()

        # transmogrify names
        log.debug("ITEMS: %s" % items)
        for key in items:
            # replace key name with mapping name, defaulting to key name
            remote.data[cls.items_to_data.get(key, key)] = items[key]

        # the section name takes precendence over a 'name' in the items
        remote.name = OstreeRemote.name_from_section(section)
        return remote

    @staticmethod
    def name_from_section(section):
        """Parse the remote name from the name of the config file section.

        ie, 'remote "awesome-os-7-ostree"' -> "awesome-os-7-ostree".
        """
        matcher = re.compile(REMOTE_SECTION_MATCH)
        result = matcher.match(section)
        log.debug("result %s" % result)
        if result:
            return result.groupdict()['remote_name']

        # FIXME
        raise RemoteSectionNameParseError

    @classmethod
    def from_content(cls, content):
        """Create a OstreeRemote object based on a rhsm.certificate.Content object.

        'content' is a rhsm.certificate.Content, as found in a
          EntitlementCertificate.contents

        This maps:
            Content.label -> OstreeRemote.name
            Content.url -> OstreeRemote.url

        OstreeRemote.branches is always None for now.
        """

        remote = cls()
        remote.name = content.label
        remote.url = content.url

        # TODO: logic for mapping content gpgkey settings to gpg_verify

        return remote

    def __repr__(self):
        r = super(OstreeRemote, self).__repr__()
        return '<%s name=%s url=%s gpg_verify=%s>' % (r, self.name, self.url, self.gpg_verify)

    def report(self):
        self.report_template = """remote \"{self.name}\"
    url: {self.url}
    gpg-verify: {self.gpg_verify}"""
        return self.report_template.format(self=self)


class OstreeRemotes(object):
    """A container/set of OstreeRemote objects.

    Representing OstreeRemote's as found in the repo configs, or
    as created from ent cert Content objects.
    """
    def __init__(self):
        self.data = []

    def add(self, ostree_remote):
        self.data.append(ostree_remote)

    # we can iterate over OstreeRemotes
    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    @classmethod
    def from_config(cls, repo_config):
        """Create a OstreeRemotes from a repo_file.RepoFile object."""
        remotes = cls()
        sections = repo_config.remote_sections()
        for section in sections:
            log.debug("section: |%s|" % section)
            item_list = repo_config.config_parser.items(section)
            log.debug("item_list: %s" % item_list)
            items = dict(item_list)
            log.debug("items: %s" % items)
            remote = OstreeRemote.from_config_section(section, items)
            remotes.add(remote)
        return remotes

    def __str__(self):
        s = "\n%s\n" % self.__class__
        for remote in self.data:
            s = s + " %s\n" % repr(remote)
        s = s + "</OstreeRemotes>\n"
        return s


class OstreeRepo(object):
    pass


class OstreeRefspec(object):
    pass


# TODO: Should be a container
class OstreeOrigin(object):
    pass

# whatever is in config:[core]
# TODO: Should probably just be a container of key, value maps
class OstreeCore(dict):
    pass


class OstreeConfigRepoConfigFileLoader(object):
    """Load the repo config file and populate a OstreeConfig.

        Could be a classmethod of OstreeConfig.

        This is the assocation between a OstreeConfig and
        the specific config file(s) that it was read from
        (/ostree/repo/config).
    """

    def __init__(self, repo_config_path):
        self.repo_config_path = repo_config_path
        self.remotes = None
        self.core = None

        # This

    def load(self):
        """Read ostree repo config, and populate it's data.

        Raises ConfigParser.Error based exceptions if there is no config or
        errors reading it.
        """
        # TODO: when/where do we create it the first time?
        self.repo_config = repo_file.RepoFile(self.repo_config_path)
        self.load_remotes()
        self.load_core()

    def load_remotes(self):
        log.debug("%s load_remotes" % __name__)
        self.remotes = OstreeRemotes.from_config(self.repo_config)
        log.debug("load_remotes: %s" % self.remotes)

    def load_core(self):
        self.core = OstreeCore()
        self.core['repo_version'] = self.repo_config.config_parser.get('core', 'repo_version')
        self.core['mode'] = self.repo_config.config_parser.get('core', 'mode')


# persist OstreeConfig object to a config file
class OstreeConfigRepoConfigFileSave(object):
    """Populate config file parser with infrom from OstreeConfig and save."""
    def __init__(self, repo_config_file):
        self.repo_config_file = repo_config_file

    def save(self, ostree_config):
        """Persist ostree_config to self.repo_config_file."""
        log.debug("ostreeRepoConfigFileLoader.save %s" % ostree_config)

        # TODO: update sections, instead of deleting all and rewriting
        # may mean OstreeConfigUpdates needs to track old remote -> Content ->
        # new remote
        self.repo_config_file.clear_remotes()

        self.update_remotes(ostree_config)
        self.update_core(ostree_config)
        self.repo_config_file.save()

    # serialize OstreeConfig more generally
    def update_remotes(self, ostree_config):
        """Update the OstreeConfig ostree_config's config file with it's new remotes."""
        # TODO: we need to figure out how to update sections
        #    this only removes all and adds new ones
        for remote in ostree_config.remotes:
            self.repo_config_file.set_remote(remote)

    def update_core(self, ostree_config):
        """Update core section in OstreeConfig ostree_config's config file if need be."""
        self.repo_config_file.set_core(ostree_config.core)


class OstreeOriginUpdater(object):
    """
    Determines the currently deployed osname and SHA256.origin file,
    and update the remote name to point to what is subscribed.

    In the event that our repo config carries multiple remote names,
    we currently select the first.
    """
    # TODO: solidify what should happen if there are multiple repos in config.
    def __init__(self, repo_config):
        # Already updated repo_config:
        self.repo_config = repo_config

    def _get_deployed_origin(self):
        """
        Get path to the currently deployed origin file.
        """
        # This is a tricky dep to satisfy. Isolated in this method so we can
        # mock it out easily in tests, which will probably never have
        # this available.
        log.debug("sys.path: %s" % sys.path)
        from gi.repository import OSTree
        sysroot = OSTree.Sysroot.new_default()
        sysroot.load(None)
        booted = sysroot.get_booted_deployment()
        #booted.get_osname()
        deploydir = sysroot.get_deployment_directory(booted)
        return sysroot.get_deployment_origin_path(deploydir)

    def run(self):
        """
        Locate and update the currently deployed origin file.
        """


        # FIXME: return early till we figure out gi/gobject conflicts
        return


        self.originfile = self._get_deployed_origin()
        log.debug("Loading ostree origin file: %s" % self.originfile)
        origin_cfg = repo_file.OriginFileConfigParser(self.originfile)
        old_refspec = origin_cfg.get('origin', 'refspec')

        # TODO: If our repo config has multiple remotes in it, which should we use?
        # For now we are just using a random one from the set:
        if len(self.repo_config.remotes):
            log.warn("Multiple remotes configured in %s." % self.repo_config)

        new_remote = self.repo_config.remotes[0].name
        new_refspec = repo_file.replace_refspec_remote(old_refspec,
            new_remote)

        if new_refspec != old_refspec:
            log.info("Updating refspec in: %s" % self.originfile)
            log.info("    old = %s" % old_refspec)
            log.info("    new = %s" % new_refspec)
            origin_cfg.set('origin', 'refspec', new_refspec)
            origin_cfg.save()
        else:
            log.debug("No change to refspec in %s" % self.originfile)


class OstreeConfigUpdatesBuilder(object):
    def __init__(self, ostree_config, content_set):
        self.orig_ostree_config = ostree_config
        self.content_set = content_set

    def build(self):
        """Figure out what the new config should be and return a OstreeConfigUpdates.

        Currently, this just creates a new OstreeRemotes containing all the remotes
        in self.content_set. It does no filter or mapping.
        """
        # NOTE: Assume 1 content == 1 remote.
        # If that's not valid, this has to do more.
        new_remotes = OstreeRemotes()

        content_to_remote = {}
        log.debug("builder.build %s" % self.content_set)
        for content in self.content_set:
            # TODO: we may need to keep a map of original config
            #       remotes -> old Content, old Content -> new Content,
            #       and new Content -> new Remotes.
            #       This does not create that map yet.
            remote = OstreeRemote.from_content(content)
            new_remotes.add(remote)

            # track for reports
            # mutliple contents to the same remote?
            content_to_remote[content] = remote

        new_ostree_config = self.orig_ostree_config.copy()
        ostree_config_updates = OstreeConfigUpdates(self.orig_ostree_config, new_ostree_config)
        ostree_config_updates.content_to_remote = content_to_remote

        return ostree_config_updates


class OstreeConfig(object):
    """Represents the config state of the systems ostree tool.

    Config file loading and parsing will create one of these and
    populate it with info.

    OstreeConfig saving serializes OstreeConfig state to the
    configuration files.
    """
    repo_config_path = OSTREE_REPO_CONFIG_PATH

    def __init__(self, core=None, remotes=None, repo_config_path=None):
        self.remotes = remotes
        self.core = core
        if repo_config_path:
            self.repo_config_path = repo_config_path

    # Unsure where the code to (de)serialize, and then persist these should
    # live. Here? OstreeConfigController? The Config file classes?
    # TODO: Should this be a part of the constructor?
    def load(self):
        """Load a ostree config files and populate OstreeConfig."""

        self.repo_config_loader = OstreeConfigRepoConfigFileLoader(
            self.repo_config_path)
        self.repo_config_loader.load()

        self.remotes = self.repo_config_loader.remotes
        self.core = self.repo_config_loader.core

    def save(self):
        """Persist OstreeConfig state to ostree config files."""
        log.debug("OstreeConfig.save")

        # Careful, we're calling this a file, it's a RepoFile, just above
        # this variable name is actually a filepath.
        repo_config_file = self.repo_config_loader.repo_config
        repo_config_file_saver = OstreeConfigRepoConfigFileSave(
            repo_config_file=repo_config_file)
        repo_config_file_saver.save(self)

    def copy(self):
        new_ostree_config = copy.deepcopy(self)
        return new_ostree_config

    def __repr__(self):
        s = []
        s.append("<OsTreeConfig file=%s>" % self.repo_config_path)
        s.append("Core: %s" % self.core)
        s.append("Remotes: %s" % self.remotes)
        return '\n'.join(s)


class OstreeConfigUpdates(object):
    """The info a ostree update action needs to update OstreeConfig.

    remote sets, origin, refspec, branches, etc.

    Try to keep track of any X->Y changes for reporting.
    """
    def __init__(self, orig, new):
        self.orig = orig
        self.new = new
        self.content_to_remote = {}

    def apply(self):
        self.orig = self.new

    def save(self):
        """Persist self.ostree_config to disk."""
        log.debug("OstreeConfigUpdates.save")
        self.orig.save()

