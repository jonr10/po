from bs4 import BeautifulSoup
import lxml
import bs4
import re
import os
import json
import urllib.request
import requests
from dateutil import parser
from datetime import datetime, date
import moment
import calendar
import csv
from slackclient import SlackClient
import botguts
from pocket import Pocket, PocketException

def is_valid_date(string):
	today = datetime.today()
	try:
		x = parser.parse(string).replace(tzinfo=None)
		if 1000 > (today - x).days > 0:
			return x.date().strftime("%d/%m/%Y")
	except ValueError:
		return False
	return False


def smmry(link, smm):
    apilink = "http://api.smmry.com/&SM_API_KEY=" + \
        smm + "&SM_LENGTH=5&SM_URL=" + link
    tesSUM = requests.get(apilink)
    return tesSUM.json()

def is_date(string):
	try:
		x = parser.parse(string)
		return x.date().strftime("%d/%m/%Y")
	except ValueError:
		return False


def find_date(string):
    string = string.split(' ')
    l = len(string)
    for k in range(l):
        if is_date(string[k]):
            i = k
            j = k + 1
            while is_date(' '.join(string[i:j])) and j < l + 1:
                j += 1
            return is_valid_date(' '.join(string[i:j - 1]))
    return False

pocket_tokens = [os.environ.get(person + "_POCKET")
                                for person in ["BOWDITCH", "FARAI", "COXON"]]

pocket_tokens
c_key = os.environ.get("POCKET_TOKEN")
SMMRY_API = os.environ.get('SMMRY_API')
links = {}
tt =[]
since = None
wanted_fields = set(['resolved_url', 'given_url', 'given_title', 'resolved_url', 'tags', 'resolved_title'])

for pock_toke in pocket_tokens:
    p = Pocket(consumer_key = c_key, access_token = pock_toke)
    poks = p.get(sort = 'newest', detailType = 'complete', since = since)[0] #tag, since parameters too
    #print(poks)
    for key in poks['list']:
        if key == '1502819':
            print('skip')
            continue
        # print(poks['list'][key].keys())
        item = poks['list'][key].keys()
        links[key] = {k:poks['list'][key][k] for k in item if k in wanted_fields}

        #links[key] = {'url' : poks['list'][key]['given_url'], 'title' : poks['list'][key]['given_title'], \
        #'tags': poks['list'][key]['tags']}
link_keys = [k for k in links]

e = requests.Session()
e.headers.update({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.68 Safari/537.36'})
lRow = []
for y in link_keys:
    lDict = {'Topic(s)':"", 'Date Added':datetime.today().strftime("%d/%m/%Y"), 'Date of Material':"", 'Contributor':"SlackBot", 'Type':"Google Alert News", 'Link':"", 'Title or Brief Description':"", 'Summary':""}
    if 'resolved_url' in links[y]:
        lDict['Link'] = links[y]['resolved_url']
    else:
        lDict['Link'] = links[y]['given_url']
    f = e.get(links[y]['given_url']) #error handle here, pdf check?
    f = BeautifulSoup(f.text,'html.parser')


    for thing in f(["script","style","head","a"]):
        thing.extract()
    text = f.get_text()
    lines = [line.strip().replace('.',':') for line in text.splitlines()]
    # chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
    textOut = '\n'.join(line for line in lines if line)


    dates = [is_date(line) for line in lines if is_date(line)]


    if len(dates)>0:
        # print(dates[0])
        lDict['Date of Material'] = dates[0]
    else:
        for line in textOut.split('\n'):
            # print(line)
            if find_date(line):
                # print(find_date(line))
                lDict['Date of Material'] = find_date(line)
                break
    summary = smmry(links[y]['given_url'], SMMRY_API)

    if 'sm_api_title' in summary:
        lDict['Title or Brief Description'] = summary['sm_api_title'].replace("\\","")
        lDict['Summary'] = summary['sm_api_content'].replace(".", ".\n\n")
        print(summary['sm_api_limitation'])
    else:
        titles = [cand.get_text().strip() for cand in f("h1")][::-1]
    # print(titles)
        while len(titles)>0:
            if len(titles[-1])>0 and len(lDict['Title or Brief Description']) < 3:
            # print(titles[-1])
                lDict['Title or Brief Description'] = titles[-1]
                break
            titles.pop()
    if "tags" in links[y]:
        lDict['Topic(s)'] = ", ".join(links[y]['tags'].keys())

    lRow.append(lDict)

tstamp = moment.now().format('MMM_DD_YYYY')
with open(tstamp + '_bot_summary.csv', 'w', encoding='utf-8') as csvfile:
    fieldnames = ['Topic(s)', 'Date Added', 'Date of Material', 'Contributor', 'Type', 'Link', 'Title or Brief Description', 'Summary']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in lRow:
        writer.writerow(row)

with open(tstamp + '_bot_summary.csv', 'r') as csvfile:
    testf = slack_client.api_call("files.upload", file = csvfile, filename = tstamp + '_bot_summary.csv', channels = chan)
# print(testf)
return "There you go!"
