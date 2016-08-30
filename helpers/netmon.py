#!/usr/bin/python

# Simple network monitor - 1s interval csv stats dumper
# Copyright (c) 2016 Lars Baumgaertner, Jonas Hoechst
#
# requires dpkt and pcap python packages
#
# usage: sudo ./netmon.py <networkinterface>

from __future__ import print_function
import dpkt, pcap
import signal
import sys
import time
from threading import Thread

total_cnt = {"pkt":0, "ip":0, "tcp":0, "udp":0, "tcp_port":0, "udp_port":0}
total_size = {"pkt":0, "ip":0, "tcp":0, "udp":0,"tcp_port":0, "udp_port":0}

cur_cnt = {"pkt":0, "ip":0, "tcp":0, "udp":0, "tcp_port":0, "udp_port":0}
cur_size = {"pkt":0, "ip":0, "tcp":0, "udp":0, "tcp_port":0, "udp_port":0}

def get_header():
    return "timestamp_ms,cnt_pkt,cnt_ip,cnt_tcp,cnt_udp,cnt_tcp_port,cnt_udp_port,size_pkt,size_ip,size_tcp,size_udp,size_tcp_port,size_udp_port\n"

def get_total_stats_human():
    out = "\\n" , "="*40
    out +="\n"+"Packet counts total:"
    out +="\n"+ "# Pkts: ", total_cnt["pkt"]
    out +="\n"+ "# IP: ", total_cnt["ip"]
    out +="\n"+ "# tcp: ", total_cnt["tcp"]
    out +="\n"+ "# udp: ", total_cnt["udp"]
    out +="\n"+ "# tcp_port: ", total_cnt["tcp_port"]
    out +="\n"+ "# udp_port: ", total_cnt["udp_port"]
    out +="\n"+ "\\nPacket size counts total:"
    out +="\n"+ "Pkts: ", total_size["pkt"]
    out +="\n"+ "IP: ", total_size["ip"]
    out +="\n"+ "tcp: ", total_size["tcp"]
    out +="\n"+ "udp: ", total_size["udp"]
    out +="\n"+ "tcp_port: ", total_size["tcp_port"]
    out +="\n"+ "udp_port: ", total_size["udp_port"] + "\n"
    return out

def get_total_stats():
    csv_line = "TOTAL,"
    csv_line += "%d,%d,%d,%d,%d,%d" % (total_cnt["pkt"],total_cnt["ip"],total_cnt["tcp"],total_cnt["udp"],total_cnt["tcp_port"],total_cnt["udp_port"])
    csv_line += ",%d,%d,%d,%d,%d,%d" % (total_size["pkt"],total_size["ip"],total_size["tcp"],total_size["udp"],total_size["tcp_port"],total_size["udp_port"])
    csv_line += "\n"
    return csv_line

def get_cur_stats():
    cur_time = int(time.time() * 1000)
    csv_line = str(cur_time) + ","
    csv_line += "%d,%d,%d,%d,%d,%d" % (cur_cnt["pkt"],cur_cnt["ip"],cur_cnt["tcp"],cur_cnt["udp"],cur_cnt["tcp_port"],cur_cnt["udp_port"])
    csv_line += ",%d,%d,%d,%d,%d,%d" % (cur_size["pkt"],cur_size["ip"],cur_size["tcp"],cur_size["udp"],cur_size["tcp_port"],cur_size["udp_port"])
    csv_line += "\n"

    for i in cur_cnt.keys(): cur_cnt[i] = 0
    for i in cur_size.keys(): cur_size[i] = 0

    last_time = cur_time
    return csv_line


class LoggerThread(Thread):
    def __init__(self, outpath=None):
        Thread.__init__(self)
        try:
            if outpath: self.outfile = open(outpath, "w+")
            else: self.outfile = None
        except IOError:
            sys.exit("Unable to write to file {}; using stdout".format(outpath))
            self.outfile = None
    
    def write(self, msg):
        if self.outfile: self.outfile.write(msg)
        else: print(msg, end="") 
    
    def run(self):
        self.write(get_header())
        self.running = True
        while self.running:
            stats = get_cur_stats()
            self.write(stats)
            sys.stdout.flush()
            time.sleep(1)
        
    def stop(self): self.running = False



class PcapThread(Thread):
    def __init__(self, interface, port=None):
        Thread.__init__(self)
        self.pc = pcap.pcap(name=interface)
        self.last_time = time.time()
        self.port = port
        
    def run(self):
        self.running = True
        while self.running: 
            self.count_pkts()

    def stop(self): self.running = False
    
    def count_pkts(self):
        for timestamp, raw_buf in self.pc:
            if not self.running: return
            
            try: self.count_pkt(raw_buf)
            except Exception as e: 
                print(e, file=sys.stderr)
            
    def count_pkt(self, raw_buf):
        if not self.running: return
        output = {}

        # Unpack the Ethernet frame (mac src/dst, ethertype)
        eth = dpkt.ethernet.Ethernet(raw_buf)
        packet_size = len(raw_buf)
        
        global cur_cnt, total_cnt, cur_size, total_size
        cur_cnt["pkt"] += 1
        total_cnt["pkt"] += 1

        cur_size["pkt"] += packet_size
        total_size["pkt"] += packet_size

        if eth.type != dpkt.ethernet.ETH_TYPE_IP: return
        
        ip = eth.data

        cur_cnt["ip"] += 1
        total_cnt["ip"] += 1

        cur_size["ip"] += packet_size
        total_size["ip"] += packet_size

        if ip.p==dpkt.ip.IP_PROTO_TCP:
           TCP=ip.data
           cur_cnt["tcp"] += 1
           total_cnt["tcp"] += 1
           cur_size["tcp"] += packet_size
           total_size["tcp"] += packet_size
           if self.port != None and (TCP.dport == self.port or TCP.sport == self.port):
               cur_cnt["tcp_port"] += 1
               total_cnt["tcp_port"] += 1
               cur_size["tcp_port"] += packet_size
               total_size["tcp_port"] += packet_size

        elif ip.p==dpkt.ip.IP_PROTO_UDP:
           UDP=ip.data
           cur_cnt["udp"] += 1
           total_cnt["udp"] += 1
           cur_size["udp"] += packet_size
           total_size["udp"] += packet_size
           if self.port != None and (UDP.dport == self.port or UDP.sport == self.port):
               cur_cnt["udp_port"] += 1
               total_cnt["udp_port"] += 1
               cur_size["udp_port"] += packet_size
               total_size["udp_port"] += packet_size


def start(interface, port=None, outpath=None):
    """Start a netmon for the given interface name
    
    port: count spare traffic for this port
    outpath: save netmon log to this port, instead of printing 
    """
    global pcapThread, loggerThread
    pcapThread = PcapThread(interface, port=port)
    loggerThread = LoggerThread(outpath=outpath)
    pcapThread.start()
    loggerThread.start()

def stop():
    """Stop the current netmon instance
    """
    global pcapThread, loggerThread
    pcapThread.stop()
    loggerThread.stop()
    pcapThread.join()
    loggerThread.join()


if __name__ == "__main__":
    if len(sys.argv) != 2: 
        print("usage: {} <interface>".format(sys.argv[0]))
        sys.exit(1)
    start(sys.argv[1])
    
    def signal_handler(signal, frame):
        stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    while True: time.sleep(60)