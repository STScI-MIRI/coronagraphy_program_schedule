"""
Script courtesy of Mike Engesser
"""
#!/usr/bin/env python3

import os,sys
import re
import subprocess
import requests
import traceback
import urllib3
import xmltodict
from bs4 import BeautifulSoup

import pandas as pd
# import numpy as np

from datetime import datetime
# from astropy.time import Time

months = {'Jan':'01','Feb':'02','Mar':'03',
          'Apr':'04','May':'05','Jun':'06',
          'Jul':'07','Aug':'08','Sep':'09',
          'Oct':'10','Nov':'11','Dec':'12'}

def getxml(url="https://yoursite/your.xml"):
    http = urllib3.PoolManager()

    response = http.request('GET', url)
    try:
        data = xmltodict.parse(response.data)
    except:
        logging(log, "Failed to parse xml from response (%s)" % traceback.format_exc())
        data = {}
        
    return data

def visit_xml(proposal_id=1234):
    url = f"https://www.stsci.edu/cgi-bin/get-visit-status?id={proposal_id}&markupFormat=xml&observatory=JWST"
    data = getxml(url=url)
    if 'visitStatusReport' in data:
        data = data['visitStatusReport']
        
    return data

def prop_html(proposal_id=1234):
    proposal_id = int(proposal_id)
    vgm_url = f"https://www.stsci.edu/cgi-bin/get-proposal-info?id={proposal_id}&observatory=JWST"
    html_text = requests.get(vgm_url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup

def program_info(proposal_id=1234):
    
    soup = prop_html(proposal_id=proposal_id)
    meta = {'proposal_id':proposal_id}
    meta['raw'] = str(soup)
    
    keys = [
        ('Principal Investigator', 'pi'),
        ('PI Institution', 'inst'),
        ('Title', 'title'),
        ('Cycle', 'cycle'),
        ('Allocation', 'allocation'),
        ('Program Status', 'type'),
        ('MIRI Reviewer', 'miri_is'),
    ]
    for k in keys:
        pattern = re.compile(f"(?<=<b>{k[0]}:</b>)(.*?)(?=<a|<br/>)")
        match = re.search(pattern, str(soup))
        if match is not None:
            match_val = match.group().strip()
            meta[k[1]] = match_val
        else:
            meta[k[1]] = '_'
        
    visits = visit_xml(proposal_id)
    #for k in ['visit']: #visits:
    #    meta[k] = visits[k]
    if isinstance(visits['visit'], list):
        meta['visit'] = visits['visit']
    else:
        meta['visit'] = [visits['visit']]
        
    return meta

def get_start_end(tv):
    if 'planWindow' not in tv:
        if 'startTime' not in tv.keys():
            return
        start = tv['startTime'].split()
        end = tv['endTime'].split()
        month = months[start[0]]
        start[0] = start[2]
        start[2] = start[1]
        start[1] = month

        month = months[end[0]]
        end[0] = end[2]
        end[2] = end[1]
        end[1] = month
        start = datetime.fromisoformat('-'.join(start[:-1]).replace(',','')+'T'+start[-1])
        end = datetime.fromisoformat('-'.join(end[:-1]).replace(',','')+'T'+end[-1])
    else:
        try:
            tv['planWindow'] = tv['planWindow'].replace(',','')
        except:
            tv['planWindow'] = tv['planWindow'][0]
            tv['planWindow'] = tv['planWindow'].replace(',','')
        start = tv['planWindow'].split('-')[0].split()
        end = tv['planWindow'].split('-')[1].split('(')[0].split()
        month = months[start[0]]
        start[0] = start[-1]
        start[-1] = start[1]
        start[1] = month
        month = months[end[0]]
        end[0] = end[-1]
        end[-1] = start[1]
        end[1] = month
        start = datetime.fromisoformat('-'.join(start)+'T00:00:00')
        end = datetime.fromisoformat('-'.join(end))
    return start, end  # returns an mjd for simplicity

def logging(log_name, message):
    
        f = open(log_name,'a')
        
        logtime = datetime.now().isoformat()

        f.write(logtime + ': ' + message + '\n')

        f.close()

        return 

def get_dates(pid, obs_id, log_name):
    
    global log
    
    log = log_name
    
    try:
        obs_meta = program_info(pid)
    except:
        logging(log, 'Could not get program info for {}.'.format(pid))
        start, end = pd.NA, pd.NA
        pass


    #print(row.sn_id, row.obs_id, row.proposal_id)
    try:
        vis = str(int(obs_id[11:13]))
        obs = str(int(obs_id[8:10]))
    except:
        try:
            vis = str(int(obs_id[16:18]))
            obs = str(int(obs_id[10:12]))
        except:
            vis = str(int(obs_id[15:17]))
            obs = str(int(obs_id[10:12])) 

    logging(log, 'Found obs and vis {}, {}...'.format(obs,vis))

    starts = []
    ends = []

    try:
        for visit in obs_meta['visit']:
            if visit['@observation']==obs and visit['@visit'] == vis:

                logging(log, 'Getting dates for {}...'.format(obs_id))
                #print(visit['target'])

                try:
                    start, end = get_start_end(visit)
                except:
                    logging(log, 'Could not get start and end times.')
                    start, end = pd.NA, pd.NA

                starts.append(start.value)
                ends.append(end.value)

                logging(log, 'Found dates {}, {}\n'.format(start, end))

                pass
    except:
        logging(log, 'Could not parse visit data, moving on.....\n')
        return
