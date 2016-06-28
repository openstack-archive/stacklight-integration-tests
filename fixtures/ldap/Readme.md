# Installation of the LDAP server

## On the node where the plugin is running

To install the server just run the script **install_ldap.sh** as root. It will
perform the following actions:

- installs the *slapd* (a LDAP daemon) and configure the DN to "dc=stacklight,dc=ci"
  - It creates the admin user: *cn=admin,dc=stacklight,dc=ci*
- creates groups and users needed for the CI tests.
  - two groups are created under the Organization Unit *groups*
    - *plugin_admins* that is the admins group
    - *plugin_viewers* that is the viewers group
  - two users that are:
    - *uadmin* user that will belong to admins group
    - *uviewer* user that will belong to viewers group

To check that everything works well you can perform the following search
that should show all inputs listed above.
```
ldapsearch -x -b "dc=stacklight,dc=ci" -D "cn=admin,dc=stacklight,dc=ci" -W
```

## Manual configuration of LDAPs

Once installed you need to perform following steps as root:

- modify */etc/default/slapd* to add LDAPS service
```
SLAPD_SERVICES="ldaps:/// ldapi:///"
```
- create a directory */etc/ldap/ssl*
- download the certificate [slapd.pem](https://raw.githubusercontent.com/openstack/stacklight-integration-tests/master/fixtures/ldap/slapd.pem) into this directory
- make this readable to openldap only
  - chown -R openldap:openldap /etc/ldap/ssl
  - chmod 0400 /etc/ldap/ssl/slapd.pem
- download the file [ldaps.ldif](https://raw.githubusercontent.com/openstack/stacklight-integration-tests/master/fixtures/ldap/ldaps.ldif) into /root/
- configure LDAP by running:
```
ldapmodify -Y EXTERNAL -H ldapi:/// -f /root/ldaps.ldif
```
- restart ldap
```
/etc/init.d/slapd restart
```
- check that the daemon is listening on port 636
```
openssl s_client -connect localhost:636 -showcerts
```
You should see information about connection and certificate. Hit Ctrl-C to quit openssl.
