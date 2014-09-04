from distutils import dir_util

from subscription_manager.base_plugin import SubManPlugin

requires_api_version = "1.0"

class DockerCertificatesPlugin(SubManPlugin):
    """
    Plugin to prep a docker build host for entitlements

    docker client temporarily copies all files from /etc/docker/secret
    into build container. Plugin copies entitlement certs and the
    redhat.repo file into this directory. The redhat.repo file is updated
    so entitlement certs and keys container path is /run/secret.
    """
    def post_subscribe_hook(self, conduit):
        entitlement_certs_dir = "/etc/pki/entitlement"
        docker_certs_dir = "/etc/docker/certs.d/redhat.com"

        # New  pem files are not written to /etc/pki/entitlement until later
        # grab them from the obj and write files
        for entitlement in conduit.entitlement_data:
            for cert in entitlement['certificates']:
                # NOTE: this is not the correct id but it does not matter
                cert_id = cert['id']
                conduit.log.debug("CERT: %s" % cert_id)
                # sslclient.cert
                cert_file = open("%s/%s.cert" % (docker_certs_dir, cert_id), "w")
                cert_file.write(cert['cert'])
                cert_file.close()
                # sslclient.key
                certkey_file = open("%s/%s.key" % (docker_certs_dir, cert_id), "w")
                certkey_file.write(cert['key'])
                certkey_file.close()
                conduit.log.info("New SSL client certificate and key %s added" % cert_id)

