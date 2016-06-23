#!/bin/bash
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

# The distinguished name of objects that will be created in LDAP
UID_UADMIN="uid=uadmin,dc=stacklight,dc=ci"
UID_UVIEWER="uid=uviewer,dc=stacklight,dc=ci"
OU_GROUPS="ou=groups,dc=stacklight,dc=ci"
CN_ADMINS="cn=plugin_admins,ou=groups,dc=stacklight,dc=ci"
CN_VIEWERS="cn=plugin_viewers,ou=groups,dc=stacklight,dc=ci"

debconf-set-selections << EOF
slapd slapd/password1 password ${PASSWORD}
slapd slapd/password1 seen true
slapd slapd/password2 password ${PASSWORD}
slapd slapd/password2 seen true
slapd slapd/domain string ${MY_DOMAIN}
slapd slapd/domain seen true
EOF

DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::=--force-confnew --no-install-recommends slapd ldap-utils

# ############################################################################
# Configure the LDAP database
#
ldapadd -x -D "cn=admin,dc=stacklight,dc=ci" \
        -w "${PASSWORD}" << EOF
# LDIF:  dc=stacklight,dc=ci
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

TMPFILE=$(mktemp -t ldapsearch-output.XXXXX)

ldapsearch -x -b "dc=stacklight,dc=ci" \
           -D "cn=admin,dc=stacklight,dc=ci" \
           -w ${PASSWORD} > "${TMPFILE}"

function check_ldap_value {
    grep "$1" "${TMPFILE}" &>/dev/null
    local status=$?
    if [ "$status" -ne 0 ]; then
        echo "  [FAILURE] $1 not found in LDAP"
    else
        echo "  [SUCCESS] $1 found in LDAP"
    fi
}

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
