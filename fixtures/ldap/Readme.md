# Installation of the LDAP server

## On the node where the plugin is running

We probably can install the LDAP server elsewhere but for testing we choose
to install it on local host to avoid problems like firwall misconfigurations.

To install the server just run the script **install_ldap.sh** as root. It will
perform the following actions:

- installs the *slapd* (a LDAP daemon) and configure the DN to "dc=stacklight,dc=ci"
  - It creates the admin user: *cn=admin,dc=stacklight,dc=ci*
- creates groups and users needed for the CI tests.
  - two groups are created under the Organization Unit *groups*
    - *plugin_admins*: the admins groups
    - *plugin_viewers*: the viewers groups
  - two users that are:
    - *uadmin*: user admin that will belong to admins group
    - *uviewer*: user viewer that will belong to viewers group

To check that every is fine you can do the following search that should show
all inputs listed above.
```
ldapsearch -x -b "dc=stacklight,dc=ci" -D "cn=admin,dc=stacklight,dc=ci" -W
```
