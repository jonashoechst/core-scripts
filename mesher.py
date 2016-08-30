#!/usr/bin/env python
from core import pycore
from core import service
from threading import Timer
import datetime, time, shutil, os, sys, signal
import helpers.netmon as netmon

myservices_path = "/home/hoechst/.core/myservices"
scheduler_targer = "/tmp/scheduler.js"
services = "DefaultRoute|MesherService"

def createLogfolder(description=None):
    start_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M')
    logfolder = "/tmp/mesher-monitor/"
    if description: logfolder += "{}-".format(description)
    logfolder += start_time
    
    if os.path.isdir(logfolder):
        char = 97
        while os.path.isdir("{}-{}".format(logfolder, chr(char))): char += 1
        logfolder = "{}-{}".format(logfolder, chr(char))
        
    os.makedirs(logfolder)
    return logfolder

def runMesherExperiment(duration, node_cnt, logfolder, scheduler=None):
    def createCoreNode(node_number, cable):
        if node_number < 1 or node_number > 254:
            raise Exception("0 < node_number < 256, since we use 10.0.0.0/24")
        node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(i))
        node.newnetif(cable, ["10.0.0.{}/24".format(i)])
        session.services.addservicestonode(node, "", services, verbose=False)
        return node

    def endExperiment():
        print("\n### Ending experiment, saving logfiles..."),
        netmon.stop()
        # os.mkdir("{}/netmon".format(logfolder))
        os.mkdir("{}/mesher".format(logfolder))
        for f in os.listdir(session.sessiondir):
            if f.endswith(".log"):
                # if f.startswith("netmon"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/netmon".format(logfolder))
                if f.startswith("mesher"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/mesher".format(logfolder))
                else: shutil.move("{}/{}".format(session.sessiondir, f), logfolder)
        with open("{}/configuration.csv".format(logfolder), "w+") as config:
            config.write("duration, {}\n".format(duration))
            config.write("node_cnt, {}\n".format(node_cnt))
            config.write("scheduler, {}\n".format(scheduler.split("/")[-1]))
        print("done.\n")
        session.shutdown()
    
    def copy_scheduler(scheduler):
        if not scheduler:
            print("No scheduler set, removing {}".format(scheduler_targer))
        elif not os.path.exists(scheduler):
            print("No file at \"{}\", removing {}".format(scheduler_targer))
        else:
            shutil.copyfile(scheduler, scheduler_targer)
            shutil.copyfile(scheduler, "{}/scheduler.js".format(logfolder))
            print("Scheduler successfully copied from \"{}\".".format(scheduler))

    print("Started Experiment; log files will be copied to "+logfolder)
    copy_scheduler(scheduler)

    print("### Creating CORE session.")
    session = pycore.Session(persistent=True)
    
    def signal_handler(signal, frame):
        endExperiment()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    print("### Importing custom services from {}".format(myservices_path))
    service.CoreServices(session).importcustom(myservices_path)

    print("### Creating central network hub.")
    hub = session.addobj(cls=pycore.nodes.HubNode, name="hub")
    
    print("### Attaching netmon to network hub.")
    netmon.start(hub.brname, outpath="{}/netmon-hub.csv".format(logfolder), port=8032)

    print("### Creating {} nodes with services: {}".format(node_cnt, services))
    nodes = []
    for i in range(node_cnt):
        nodes.append(createCoreNode(i+1, hub))

    print("### Starting node services...")
    for n in nodes: service.CoreServices(session).bootnodeservices(n)

    print("### Experiment is now running for {} seconds.\n".format(duration))
    time.sleep(duration)
    endExperiment()

if __name__ == "__main__":
    node_counts = [10] #[5, 10, 25, 50, 100]
    durations = [10]
    schedulers = []
    
    if len(sys.argv) != 2:
        print("usage: {} [scheduler|scheduler-dir]".format(sys.argv[0]))
        sys.exit(1)
        
    if os.path.isdir(sys.argv[1]):
        for (_, _, filenames) in os.walk(sys.argv[1]):
            for filename in filenames:
                if filename.endswith('.js'): 
                    schedulers.append(os.sep.join([sys.argv[1], filename]))
    elif os.path.isfile(sys.argv[1]) and sys.argv[1].endswith('.js'):
        schedulers.append(filename)
    else:
        print("No scheduler found at given path.\n")
        print("usage: {} [scheduler|scheduler-dir]".format(sys.argv[0]))
        sys.exit(2)
    
    for d in durations:
        for n in node_counts:
            for s in schedulers:
                sname = s.split("/")[-1]
                description = "{}-n{}".format(sname, n)
                logfolder = createLogfolder(description)
                runMesherExperiment(d, n, logfolder, scheduler=s)




