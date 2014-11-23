#!/usr/bin/env python

#
# Assumes boto variables are set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#

from xml.etree import ElementTree as etree
import boto.vpc,sys,boto,boto.ec2,socket
import requests  

# Tested on Ubuntu 14.04 with boto==2.34.0, requests==2.2.1

def clean_name(n):
  return (''.join(s for s in n if ( s.isalnum() or s == "_" or s == "-") )).upper()


############
conn = boto.ec2.EC2Connection()
regions = conn.get_all_regions()
account_id =  conn.get_all_security_groups(groupnames='default')[0].owner_id

#password = raw_input("Enter OpenNMS Admin password for REST API>").rstrip()
password = "admin"

for r in regions:
  c = boto.ec2.connect_to_region(r.name)
  v = boto.vpc.connect_to_region(r.name)

  if len(sys.argv) == 1:
    print "Usage:\n\taws2nms.py [hosts|vpcs]"
    sys.exit(-1)

  if "hosts" in sys.argv or "all" in sys.argv:
    i_dict = {}
    hosts = []  # will probably be duplicates here but uniq them out

    for res in c.get_all_instances():
      for i in res.instances:  
        # Skip private addresses
        if i.ip_address:
          if i.tags.has_key("Name"):
            identifier = clean_name(i.tags["Name"])
            i_dict[i.id] = identifier
          else:
            identifier = i.id

          hosts.append( (account_id,r.name, i.ip_address,identifier) )

    for h in hosts :
      print "Adding: %s,%s,%s,%s" % ( h[0],h[1], h[2],h[3] )

      # Taken from http://www.opennms.org/wiki/Large_Requisitions#ReST_API_Tips
      xml_template = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><node node-label="LABEL" foreign-id="LABEL"><interface snmp-primary="N" status="1" ip-addr="IPADDR"/></node>'''

      root = etree.fromstring(xml_template)
      root.set('node-label',h[3])
      root.set('foreign-id',h[3])
      iface = root.find('interface')
      iface.set('ip-addr',h[2])
      node_string = etree.tostring(root)
      r = requests.post("http://127.0.0.1:8980/opennms/rest/requisitions/importboto/nodes",auth=("admin",password),data=node_string)
      print "Response:",r.status_code
  
  if "vpcs" in sys.argv or "all" in sys.argv:
    for i in v.get_all_vpcs():
        print "%s,%s,%s,%s" % (account_id,r.name, i.cidr_block,i.id)

print "Committing requisition"
r = requests.put("http://127.0.0.1:8980/opennms/rest/requisitions/importboto/import?rescanExisting=false",auth=("admin",password))
print "Response:",r.status_code
