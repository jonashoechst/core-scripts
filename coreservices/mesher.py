#
# CORE
# Copyright (c)2010-2012 the Boeing Company.
# See the LICENSE file included in this distribution.
#
''' Mesher experimental service.
'''

import os

from core.service import CoreService, addservice
from core.misc.ipaddr import IPv4Prefix, IPv6Prefix

class MesherService(CoreService):
    # a unique name is required, without spaces
    _name = "MesherService"
    # you can create your own group here
    _group = "Mesh"
    # list of other services this service depends on
    _depends = ()
    # per-node directories
    _dirs = ()
    # generated files (without a full path this file goes in the node's dir,
    #  e.g. /tmp/pycore.12345/n1.conf/)
    _configs = ('mesher-start.sh', 'mesher-stop.sh', )
    # this controls the starting order vs other enabled services
    _startindex = 1
    # list of startup commands, also may be generated during startup
    _startup = ('bash mesher-start.sh', )
    # list of shutdown commands
    _shutdown = ('bash mesher-stop.sh', )

    @classmethod
    def generateconfig(cls, node, filename, services):
        if filename == "mesher-start.sh":
            cfg = '''#!/bin/bash
sleep 1
STIME=$(( $RANDOM % 20 )).$(( $RANDOM % 1000 ));
sleep $STIME
sched=/tmp/scheduler.js
logfile={}/mesher-{}.log
if [ -e $sched ]; then
    nohup mesher-experimental $sched &> $logfile &
else
    nohup mesher-experimental &> $logfile &
fi
echo $! > mesher.pid
'''.format(node.session.sessiondir, node.name)

        if filename == "mesher-stop.sh":
            cfg = '''#!/bin/sh
kill `cat mesher.pid`
rm mesher.pid
'''


        return cfg

    @staticmethod
    def subnetentry(x):
        ''' Generate a subnet declaration block given an IPv4 prefix string
            for inclusion in the config file.
        '''
        if x.find(":") >= 0:
            # this is an IPv6 address
            return ""
        else:
            net = IPv4Prefix(x)
            return 'echo "  network %s"' % (net)

# this line is required to add the above class to the list of available services
addservice(MesherService)
