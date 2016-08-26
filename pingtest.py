#!/usr/bin/env python

from core import pycore

node_cnt = 10

session = pycore.Session(persistent=True)

hub = session.addobj(cls=pycore.nodes.HubNode, name="hub")
nodes = []

for i in range(node_cnt):
    node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(i))
    node.newnetif(hub, ["10.0.0.{}/24".format(i)])
    nodes.append(node)
    
for n in nodes:
    for i in range(node_cnt):
        n.icmd(["ping", "-c", "1", "10.0.0.{}".format(i)])

session.shutdown()