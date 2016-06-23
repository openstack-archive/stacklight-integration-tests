#!/bin/bash
set -e

# ############################################################################
# Install the standalone LDAP server (slapd)
#
if [ "$(id -u)" -ne 0 ]
then echo "Please run as root"
    exit 1
fi

DOMAIN="stacklight.ci"
BASE_DN="dc=stacklight,dc=ci"
BIND_DN="cn=admin,${BASE_DN}"
BIND_PASSWORD="admin"

# The distinguished name of objects that will be created in LDAP
UID_UADMIN="uid=uadmin,${BASE_DN}"
UID_UVIEWER="uid=uviewer,${BASE_DN}"
OU_GROUPS="ou=groups,${BASE_DN}"
CN_ADMINS="cn=plugin_admins,${OU_GROUPS}"
CN_VIEWERS="cn=plugin_viewers,${OU_GROUPS}"

debconf-set-selections << EOF
slapd slapd/password1 password ${BIND_PASSWORD}
slapd slapd/password1 seen true
slapd slapd/password2 password ${BIND_PASSWORD}
slapd slapd/password2 seen true
slapd slapd/domain string ${DOMAIN}
slapd slapd/domain seen true
EOF

DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::=--force-confnew --no-install-recommends slapd ldap-utils

# ############################################################################
# Configure the LDAP database
#
ldapadd -x -D ${BIND_DN} -w ${BIND_PASSWORD} << EOF
# Creation of the user "uadmin" that will belong to admins group
dn: ${UID_UADMIN}
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
dn: ${UID_UVIEWER}
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
dn: ${OU_GROUPS}
objectclass: organizationalUnit
objectclass: top
ou: groups

# Creation of the admins groups
dn: ${CN_ADMINS}
cn: plugin_admins
gidnumber: 501
memberuid: uadmin
objectclass: posixGroup
objectclass: top

# Creation of the viewers groups
dn: ${CN_VIEWERS}
cn: plugin_viewers
gidnumber: 503
memberuid: uviewer
objectclass: posixGroup
objectclass: top
EOF

# ############################################################################
# Validate the installation

function check_ldap_value {
    if grep "$1" "${TMPFILE}" &>/dev/null; then
        echo "  [SUCCESS] $1 found in LDAP"
    else
        echo "  [FAILURE] $1 not found in LDAP"
    fi
}

TMPFILE=$(mktemp -t ldapsearch-output.XXXXX)
ldapsearch -x -b ${BASE_DN} -D ${BIND_DN} -w ${BIND_PASSWORD} > "${TMPFILE}"

set +e
echo "Installation and configuration of LDAP server are done."
echo "Starting the validation of the LDAP schema."
check_ldap_value $UID_UADMIN
check_ldap_value $UID_UVIEWER
check_ldap_value $OU_GROUPS
check_ldap_value $CN_ADMINS
check_ldap_value $CN_VIEWERS
echo "Validation completed. You should only see SUCCESS reported."

rm -f "${TMPFILE}"
