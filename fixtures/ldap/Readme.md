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

The server is running LDAP and LDAPS. The self-signed certificate is generated
by the script and stored in */etc/ldap/ssl/slapd.pem*.
