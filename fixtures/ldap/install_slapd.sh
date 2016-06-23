#!/bin/sh
set -e

# ############################################################################
# Install the standalone LDAP server (slapd)
#
if [ "$(id -u)" -ne 0 ]
then echo "Please run as root"
    exit 1
fi

PASSWORD="admin"
MY_DOMAIN="stacklight.ci"

PRESEED_FILE=$(mktemp -t slapd-preseed.XXXXXX)

echo "slapd slapd/password1 password ${PASSWORD}
slapd slapd/password1 seen true
slapd slapd/password2 password ${PASSWORD}
slapd slapd/password2 seen true
slapd slapd/domain string ${MY_DOMAIN}
slapd slapd/domain seen true
" > "${PRESEED_FILE}"
debconf-set-selections "${PRESEED_FILE}"
rm "${PRESEED_FILE}"

DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::=--force-confnew --no-install-recommends slapd ldap-utils

# ############################################################################
# Configure the LDAP database
#
CI_SCHEME_LDIF_FILE=$(mktemp -t ci-scheme-XXX.ldif)
cat << EOF > ${CI_SCHEME_LDIF_FILE}
# LDIF:  dc=stacklight,dc=ci
# Creation of the user "uadmin" that will belong to admins group
dn: uid=uadmin,dc=stacklight,dc=ci
cn: uadmin
gecos: uadmin
gidnumber: 500
homedirectory: /home/uadmin
loginshell: /bin/bash
objectclass: top
objectclass: account
objectclass: posixAccount
objectclass: shadowAccount
shadowlastchange: 0
shadowmax: 0
shadowwarning: 0
uid: uadmin
uidnumber: 16860
userpassword: uadmin

# Creation of the user "uviewer" that will belong to viewers group
dn: uid=uviewer,dc=stacklight,dc=ci
cn: uviewer
gecos: uviewer
gidnumber: 500
homedirectory: /home/uviewer
loginshell: /bin/bash
objectclass: top
objectclass: account
objectclass: posixAccount
objectclass: shadowAccount
shadowlastchange: 0
shadowmax: 0
shadowwarning: 0
uid: uviewer
uidnumber: 16861
userpassword: uviewer

# Creation of the Organization Unit "groups"
dn: ou=groups,dc=stacklight,dc=ci
objectclass: organizationalUnit
objectclass: top
ou: groups

# Creation of the admins groups
dn: cn=plugin_admins,ou=groups,dc=stacklight,dc=ci
cn: plugin_admins
gidnumber: 501
memberuid: uadmin
objectclass: posixGroup
objectclass: top

# Creation of the viewers groups
dn: cn=plugin_viewers,ou=groups,dc=stacklight,dc=ci
cn: plugin_viewers
gidnumber: 503
memberuid: uviewer
objectclass: posixGroup
objectclass: top
EOF

ldapadd -x -D "cn=admin,dc=stacklight,dc=ci" -w "${PASSWORD}" -f "${CI_SCHEME_LDIF_FILE}"
rm -f "${CI_SCHEME_LDIF_FILE}"

# ############################################################################
# Validate the installation

echo "
You can manually check that LDAP was properly fed by running:

ldapsearch -x -b \"dc=stacklight,dc=ci\" -D \"cn=admin,dc=stacklight,dc=ci\" -W
"
