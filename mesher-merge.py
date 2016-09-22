#!/usr/bin/env python
from core import pycore
from core import service
from threading import Timer
import datetime, time, shutil, os, sys, signal
import helpers.netmon as netmon

myservices_path = os.getcwd() + "/coreservices"
scheduler_targer = "/tmp/scheduler.js"
services = "DefaultRoute|MesherService"
log = "/tmp/mesher-monitor-merge/"

def createLogfolder(description=None):
    start_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M')
    logfolder = log
    if description: logfolder += "{}-".format(description)
    logfolder += start_time

    if os.path.isdir(logfolder):
        char = 97
        while os.path.isdir("{}-{}".format(logfolder, chr(char))): char += 1
        logfolder = "{}-{}".format(logfolder, chr(char))

    os.makedirs(logfolder)
    return logfolder

def runMesherExperiment(duration, node_cnt, logfolder, scheduler=None, delay=0):
    def createCoreNode(node_number, cable):
        if node_number < 1 or node_number > 254:
            raise Exception("0 < node_number < 256, since we use 10.0.0.0/24")
        node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(str(i).zfill(3)))
        node.newnetif(cable, ["10.0.0.{}/24".format(i)])
        session.services.addservicestonode(node, "", services, verbose=False)
        return node

    def endExperiment():
        print("### Ending experiment...")
        print("    stopping netmon")
        netmon.stop()
        # os.mkdir("{}/netmon".format(logfolder))

        print("    copying files")
        os.mkdir("{}/mesher".format(logfolder))
        for f in os.listdir(session.sessiondir):
            if f.endswith(".log"):
                # if f.startswith("netmon"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/netmon".format(logfolder))
                if f.startswith("mesher"): shutil.move("{}/{}".format(session.sessiondir, f), "{}/mesher".format(logfolder))
                else: shutil.move("{}/{}".format(session.sessiondir, f), logfolder)
        with open("{}/configuration.csv".format(logfolder), "w+") as config:
            config.write("duration, {}\n".format(duration))
            config.write("node_cnt, {}\n".format(node_cnt))
            try:
                config.write("scheduler, {}\n".format(scheduler.split("/")[-1]))
            except Exception as e:
                config.write("scheduler, {}\n".format(scheduler))

        print("    datacollecting session")
        session.datacollect()
        print("    shutting down session")
        session.shutdown()
        print("    done.\n")
        print(" Results in folder: {}\n".format(logfolder))

    def copy_scheduler(scheduler):
        if not scheduler:
            print("Warn: No scheduler set, removing {}".format(scheduler_targer))
        elif not os.path.exists(scheduler):
            print("Warn: No file at \"{}\", removing {}".format(scheduler_targer))
        else:
            shutil.copyfile(scheduler, scheduler_targer)
            shutil.copyfile(scheduler, "{}/scheduler.js".format(logfolder))

    copy_scheduler(scheduler)

    print("### Creating CORE session.")
    session = pycore.Session(persistent=True)

    def signal_handler(signal, frame):
        endExperiment()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    print("### Importing custom services from {}".format(myservices_path))
    service.CoreServices(session).importcustom(myservices_path)

    print("### Creating two network hubs.")
    hub1 = session.addobj(cls=pycore.nodes.HubNode, name="a", objid="a")
    hub2 = session.addobj(cls=pycore.nodes.HubNode, name="b", objid="b")

    print("### Creating {} nodes with services: {}".format(node_cnt, services))
    nodes = []
    for i in range(node_cnt):
        if i < node_cnt / 2: nodes.append(createCoreNode(i+1, hub1))
        else: nodes.append(createCoreNode(i+1, hub2))

    print("### Attaching netmon to both network hubs.")
    netmon.start(hub1.brname, outpath="{}/netmon-hub1.csv".format(logfolder), port=8032)
    netmon.start(hub2.brname, outpath="{}/netmon-hub2.csv".format(logfolder), port=8032)
    print("### Starting node services (with {}s delay)".format(delay))
    for n in nodes:
        service.CoreServices(session).bootnodeservices(n)
        time.sleep(delay)
        sys.stdout.write(".")

    remaining_duration = duration - len(nodes)*delay

    print("\n### Experiment is now running for first {} seconds.\n".format(remaining_duration/2))
    for i in range(remaining_duration/2):
        time.sleep(1)
        sys.stdout.write(".")

    print("\n### Merging network.")
    hub1.linknet(hub2)

    print("\n### Experiment is now running for remaining {} seconds.\n".format(remaining_duration/2))
    for i in range(remaining_duration/2):
        time.sleep(1)
        sys.stdout.write(".")

    print(" time's up!")
    endExperiment()

if __name__ == "__main__":
    node_counts = [2, 5, 10, 25, 50, 100, 200]
    d = 300 # 300s aka. 5 min.
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
        schedulers.append(sys.argv[1])
    else:
        print("No scheduler found at given path.\n")
        print("usage: {} [scheduler|scheduler-dir]".format(sys.argv[0]))
        sys.exit(2)

    count = (len(node_counts)) * len(schedulers)
    runlength = float(count * d) / 60 / 60
    print("Starting Mesher Experiment session --- {} Experiments ~ {} hours.".format(count, runlength))
    num = 1

    for n in node_counts:
        for s in schedulers:
            sname = s.split("/")[-1].split(".")[0]
            description = "{}-n{}".format(sname, str(n).zfill(3))
            logfolder = createLogfolder(description)
            print("\nRunning experiment {} / {}.".format(num, count))
            runMesherExperiment(d, n, logfolder, scheduler=s)
            num += 1
