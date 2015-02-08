#!/usr/bin/env python

# Assumes PAGERDUTYSITE PAGERDUTY are env variables to access your PagerDuty deployment
# Requires Requests 2.2.x
# 

import string,os,requests,time,datetime,re,sys

def parse_alert(service,raw,debug=False):
  """Extract host and alert type from raw alert"""
  host = "unknown"
  alert = "unknown"

  if debug:
    print "Processing alert from:", service
    print raw

  if service == "Nagios":
    # LAZY!!!!
    fields = raw.split(";")
    for f in fields:
      (k,v) = f.split("=")
      if k == "host_name":
        host = v
      elif k == "service_desc":
        alert = v
  elif service == "Nagios PD API":
    # LAZY!!!!
    fields = raw.split(";")
    for f in fields:
      (k,v) = f.split("=")
      if k == "host_name":
        host = v
      elif k == "service_desc":
        alert = v



  elif service == "OpenNMS":
    down_re = m = re.match(r"OpenNMS\sAlert:\sNotice\s#.*:(.*)\son\s(.*)\s\(",raw)
    if down_re:
      host = down_re.group(2)
      alert = down_re.group(1)
    else:
      other_re = m = re.match(r"OpenNMS\sAlert:\sNotice\s#.*:(.*)\son node\s(.*)$",raw)
      if other_re:
        host = other_re.group(2)
        alert = other_re.group(1)
  return (host,string.lstrip(alert))

class IncidentGrabber():
  def __init__(self,site,key,debug=False):
    self.debug = debug
    self.site=site
    self.headers = { "Content-type":"application/json","Authorization":"Token token="+key }
    self.payload = {}
    self.incidents = []
    self.node_stats = {}
    self.alert_stats = {}

  def get_incidents(self,days_back=30,batch_size=75):
    now = time.time()
    since = now - (60*60*24*days_back)
    start = datetime.datetime.fromtimestamp(since)
    since_str = "%d-%d-%d" % (start.year,start.month,start.day)
    payload = {"offset": 0, "since": since_str, "limit": batch_size  }

    first_request = requests.get(self.site + "/api/v1/incidents",headers=self.headers,params=payload)
    j = first_request.json()
    total_incidents = j['total']


    if self.debug:
      #print "Sent:",first_request.request.headers,first_request.request.body
      print "Incidents found in request:", j['total']

    if total_incidents > batch_size:
      offset = batch_size

      if self.debug:
        print "Greater than %s incidents" % batch_size

    for i in j['incidents']:
      service = i['service']
      alert_tuple = parse_alert(service['name'],i['incident_key'],self.debug)
      self.incidents.append((i['incident_number'],service['name'],i['last_status_change_on'],alert_tuple[0],alert_tuple[1],i['incident_key']))


    while (total_incidents > batch_size) and (offset < j['total']):
      payload = {"offset": offset,"limit": batch_size, "since": since_str  }
      r = requests.get(self.site + "/api/v1/incidents",headers=self.headers,params=payload)

      if self.debug:
        print "Reading more incidents with offset",offset


      for i in r.json()['incidents']:
        service = i['service']
        alert_tuple = parse_alert(service['name'],i['incident_key'],self.debug)
        self.incidents.append( (i['incident_number'],service['name'],i['last_status_change_on'],alert_tuple[0],alert_tuple[1],i['incident_key']))

      offset += batch_size

  def summarize_incidents(self):
    pass

  def tally_stats(self):
    for i in self.incidents:
      if "unknown" not in i:
        host = i[3][0]
        alert = i[3][1]

  def dump_to_csv(self):
    for i in self.incidents:
      if "unknown" not in i:
        for j in i:
          print j,"|",
        print
  def dump_to_json(self):
    pass

if __name__ == "__main__":
  if "PAGERDUTYSITE" not in os.environ.keys() or "PAGERDUTYKEY" not in os.environ.keys():
    print "You need to set PAGERDUTYSITE and/or PAGERDUTYKEY"
    sys.exit(-1)

  if len(sys.argv) == 2:
    daysback = int(sys.argv[1])
  else:
    daysback = 7
  #print "Searching %d days back" % daysback
  ig = IncidentGrabber(os.environ["PAGERDUTYSITE"],os.environ["PAGERDUTYKEY"])
  ig.get_incidents(daysback)
  ig.dump_to_csv()
