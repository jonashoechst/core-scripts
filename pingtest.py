#!/usr/bin/env python

from core import pycore

node_cnt = 10

session = pycore.Session(persistent=True)

hub1 = session.addobj(cls=pycore.nodes.HubNode, objid="a", name="a", verbose=True)
hub2 = session.addobj(cls=pycore.nodes.HubNode, objid="b", name="b", verbose=True)
hub1.linknet(hub2)
nodes = []

for i in range(node_cnt):
    node = session.addobj(cls=pycore.nodes.CoreNode, name="n{}".format(i))
    if i < node_cnt/2: node.newnetif(hub1, ["10.0.0.{}/24".format(i)])
    else: node.newnetif(hub2, ["10.0.0.{}/24".format(i)])
    nodes.append(node)
    
for n in nodes:
    for i in range(node_cnt):
        n.icmd(["ping", "-c", "1", "10.0.0.{}".format(i)])

session.shutdown()