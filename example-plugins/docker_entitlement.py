
from distutils import dir_util

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"

class DockerEntitlementPlugin(SubManPlugin):
    """
    Plugin to prep a docker build host for entitlements

    docker client temporarily copies all files from /etc/docker/secret
    into build container. Plugin copies entitlement certs and the
    redhat.repo file into this directory. The redhat.repo file is updated
    so entitlement certs and keys container path is /run/secret.
    """
    def post_subscribe_hook(self, conduit):
        host_secret_dir = "/etc/docker/secrets"
        container_secret_dir = "/run/secrets"
        entitlement_certs_dir = "/etc/pki/entitlement"
        repo_file = "redhat.repo"

        dir_util.copy_tree(entitlement_certs_dir, host_secret_dir, preserve_mode=1, \
            preserve_times=1, preserve_symlinks=1, update=1, verbose=1)
        conduit.log.info("Entitlement certs copied to %s" % host_secret_dir)

        repo_orig = "/etc/yum.repos.d/%s" % repo_file
        os_repo = "rhel7.repo"
        repo_new = "%s/%s" % (host_secret_dir, os_repo)
        infile = open(repo_orig, 'r')
        outfile = open(repo_new, 'w')
        for line in infile:
            line = line.replace(entitlement_certs_dir, container_secret_dir)
            outfile.write(line)
        infile.close()
        outfile.close()
        conduit.log.info("%s copied to %s" % (repo_orig, host_secret_dir))
        conduit.log.info("%s SSL client certificate and key paths updated" % repo_new)

        # New  pem files are not written to /etc/pki/entitlement until later
        # grab them from the obj and write files
        for entitlement in conduit.entitlement_data:
            for cert in entitlement['certificates']:
                # FIXME: incorrect ID!
                cert_id = cert['id']
                conduit.log.debug("CERT: %s" % cert_id)
                # sslclientcertificate.pem
                cert_file = open("%s/%s.pem" % (host_secret_dir, cert_id), "w")
                cert_file.write(cert['cert'])
                cert_file.close()
                # sslclient-key.pem
                certkey_file = open("%s/%s-key.pem" % (host_secret_dir, cert_id), "w")
                certkey_file.write(cert['key'])
                certkey_file.close()
                conduit.log.info("New SSL client certificate and key %s added" % cert_id)

