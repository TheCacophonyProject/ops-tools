This directory contains tools which are useful for managing releases
of the Cacophony Project's software.

## find-server-upgrades

This tool runs on the Salt master and finds differences in software
versions between the test and production servers. It is used to inform
promotion of software from test to production.


## find-unreleased

This tool reports changes in the Cacophony Project's Github repos
which haven't been incorporated in a tagged release yet. It is used to
guide the weekly creation of packages which need to be deployed to
test servers and devices.

It can be run from anywhere but is often run on the Salt master for
convenience.
