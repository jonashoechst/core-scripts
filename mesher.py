#!/usr/bin/env python
from core import pycore
from core import service
from threading import Timer
import datetime, time, shutil, os, sys

myservices_path = "/home/hoechst/.core/myservices"
services = "DefaultRoute|NetmonService|MesherService"

def concieveLogfolder(description):
    start_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M')
    logfolder = "/tmp/mesher-monitor/{}-{}/".format(description, start_time)
    return logfolder

def runMesherExperiment(duration, node_cnt, logfolder):
    def createCoreNode(node_number, cable):
        if node_number < 1 or node_number > 254:
            raise Exception("0 < node_number < 256, since we use 10.0.0.0/24")
        node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(i))
        node.newnetif(cable, ["10.0.0.{}/24".format(i)])
        session.services.addservicestonode(node, "", services, verbose=False)
        return node

    def endExperiment():
        print("\n### Ending experiment, saving logfiles..."),
        os.makedirs(logfolder)
        os.mkdir("{}/netmon".format(logfolder))
        os.mkdir("{}/mesher".format(logfolder))
        for f in os.listdir(session.sessiondir):
            if f.endswith(".log"):
                if f.startswith("netmon"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/netmon".format(logfolder))
                elif f.startswith("mesher"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/mesher".format(logfolder))
                else: shutil.move("{}/{}".format(session.sessiondir, f), logfolder)
        with open("{}configuration.csv".format(logfolder), "w+") as config:
            config.write("duration: {}\n".format(duration))
            config.write("node_cnt, {}\n".format(node_cnt))
        print("done.\n")
        session.shutdown()

    print("Started Experiment; log files will be copied to "+logfolder)
    print("### Creating CORE session.")
    session = pycore.Session(persistent=True)

    print("### Importing custom services from {}".format(myservices_path))
    service.CoreServices(session).importcustom(myservices_path)

    print("### Creating central network hub.")
    hub = session.addobj(cls=pycore.nodes.HubNode, name="hub")

    print("### Creating {} nodes with services: {}".format(node_cnt, services))
    nodes = []
    for i in range(node_cnt):
        nodes.append(createCoreNode(i+1, hub))

    print("\n### Scheduling experiment ending in {}s.".format(duration))
    t = Timer(duration, endExperiment)
    t.start()

    print("### Starting node services...")
    for n in nodes: service.CoreServices(session).bootnodeservices(n)

    print("### Experiment is now running.")
    t.join()

if __name__ == "__main__":
    runMesherExperiment(2, 5, concieveLogfolder("testing5"))
    runMesherExperiment(2, 10, concieveLogfolder("testing10"))
