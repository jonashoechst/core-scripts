#!/usr/bin/env python
from core import pycore
from core import service
from threading import Timer
import datetime, time, shutil, os, sys

myservices_path = "/home/hoechst/.core/myservices"
experiment_time_s = 60
node_cnt = int(sys.argv[1])

start_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M')
logfolder = "/tmp/mesher-monitor-{}/".format(start_time)
print("Started Experiment; log files will be copied to "+logfolder)

print("### Creating CORE session.")
session = pycore.Session(persistent=True)

print("### Importing custom services from {}".format(myservices_path))
service.CoreServices(session).importcustom(myservices_path)
services = "DefaultRoute|NetmonService|MesherService"

print("### Creating central network hub.")
hub = session.addobj(cls=pycore.nodes.HubNode, name="hub")
nodes = []

def createCoreNode(i):
    node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(i))
    node.newnetif(hub, ["10.0.0.{}/24".format(i)])
    session.services.addservicestonode(node, "", services, verbose=False)
    return node

print("### Creating {} nodes, with services: {}".format(node_cnt, services))
for i in range(node_cnt):
    nodes.append(createCoreNode(i+1))

def endExperiment():
    print("\n### Ending Experiment; saving logfiles..."),
    os.mkdir(logfolder)
    os.mkdir("{}/netmon".format(logfolder))
    os.mkdir("{}/mesher".format(logfolder))
    for f in os.listdir(session.sessiondir):
        if f.endswith(".log"):
            if f.startswith("netmon"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/netmon".format(logfolder))
            elif f.startswith("mesher"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/mesher".format(logfolder))
            else: shutil.move("{}/{}".format(session.sessiondir, f), logfolder)
    print("done.")
    session.shutdown()


print("\n### Scheduling Experiment ending in {}s.".format(experiment_time_s))
t = Timer(experiment_time_s, endExperiment)
t.start()

print("### Starting node services..."),
for n in nodes: service.CoreServices(session).bootnodeservices(n)
print("done.")
print("### Experiment is now running.")
