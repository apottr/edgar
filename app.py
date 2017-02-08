import requests as req
import argparse as ap
import xml.dom.minidom as xml
import re,csv,sys,os
from time import time

parser = ap.ArgumentParser()
parser.add_argument("input",help="Input must be an EDGAR CIK or Ticker.")
args = parser.parse_args()
urls = {
    'rss': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany'+
            '&CIK={cik}'+
            '&CIK={cik}'+
            '&type=13F-HR'+
            '&dateb='+
            '&owner=exclude'+
            '&start=0'+
            '&count=40'+
            '&output=atom',
    'file': 'https://www.sec.gov/Archives/edgar/data/{cik}/{acn}/{acn_full}.txt',
    'path': 'https://www.sec.gov/Archives/edgar/data/{cik}/{acn}/{path}'
            }

def get_rss(cik):
    '''
    function name: get_rss
    description:
        This function takes a CIK and pulls the RSS feed to get the forms.
    arguments:
        cik - takes a 10-digit string as an argument
    returns:
        x - parsed RSS XML
    '''
    r = req.get(urls['rss'].format(cik=cik))
    x = xml.parseString(r.text)
    if not (cik[0] in "0123456789"):
        companyInfo = x.getElementsByTagName('company-info')[0]
        cik = companyInfo.getElementsByTagName('cik')[0].childNodes
    return x,cik

def get_txt(entry,cik):
    '''
    function name: get_txt
    description:
        This function takes an RSS entry and pulls it in the SGML format.
    arguments:
        entry - single item from the RSS feed
        cik - CIK identifier
    returns:
        r.text - the detailed SGML from the RSS entry
    '''
    acn_full = entry[1].childNodes[0].toxml()
    acn = acn_full.replace('-','')
    r = req.get(urls['file'].format(cik=cik,acn=acn,acn_full=acn_full))
    return r.text,acn

def flatten_nodelists(nodelist,keys_or_values=True):
    '''
    function name: flatten_nodelists
    description:
        This function takes an XML NodeList as an argument and uses recursion to flatten
        it to a 1-dimensional array.
    arguments:
        nodelist - NodeList from processed XML
        keys_or_values - toggles pulling keys or values, defaults to pulling keys.
    returns:
        out - flattended NodeList
    '''
    out = []
    for item in nodelist:
        if len(item.childNodes) > 1:
            out += flatten_nodelists(item.childNodes,keys_or_values)
        elif len(item.childNodes) > 0:
            if keys_or_values:
                out.append(item.nodeName)
            else:
                out.append(item.childNodes[0].toxml())
    return out

def to_tsv(obj):
    '''
    function name: to_tsv
    description:
        Converts a python Dict with keys "columns" and "rows" to a "tab-separated values"
        spreadsheet with the filename "fname". If there already exists a file with that name,
        it will append the current unix timestamp to the filename before the extension.
    arguments:
        obj - Dict with keys "columns", "rows", "fname"
    returns:
        None
    '''
    if os.path.isfile(obj['fname']+'tsv'):
        fname = obj['fname']+str(time())+'.tsv'
    else:
        fname = obj['fname']+'tsv'

    with open(fname,'wb') as f:
        w = csv.writer(f,delimiter='\t')
        w.writerow(obj['columns'])
        for row in obj['rows']:
            w.writerow(row)

def to_obj(txt,cik,acn):
    '''
    function name: to_obj
    description:
        Processes SGML returned from get_txt and converts it to a dict with keys "column",
        "rows", and "fname". If it cannot find an XML table it will fail with a message.
    arguments:
        txt - SGML input
        cik - CIK Identifier
        acn - SEC Accession Number
    returns:
        obj - Dict with keys "columns", "rows", "fname"
    '''
    m = re.findall(r'<FILENAME>(.*)\n',txt)
    try:
        r = req.get(urls['path'].format(cik=cik,acn=acn,path=m[1]))
    except:
        print "Could not find XML file path, exiting..."
        sys.exit(1)
    x = xml.parseString(r.text)
    data = x.getElementsByTagName('infoTable')
    keys = data[0].childNodes
    keylist = flatten_nodelists(keys)
    rows = []
    for row in data:
        rows.append(flatten_nodelists(row.childNodes,False))
    obj = {
        'columns': keylist,
        'rows': rows,
        'fname': m[1][:-3]
            }
    return obj 

if __name__ == "__main__":
    '''
    Takes a CIK/Ticker as input, prints the CIK, finds all XML elements with the name
    "entry", and cycles through them, converting the tables contained to a TSV file.
    '''
    cik = args.input
    out,cik = get_rss(cik)
    print cik
    data = out.getElementsByTagName('entry')
    for ent in data:
        entry = ent.getElementsByTagName('content')[0].childNodes
        txt,acn = get_txt(entry,cik)
        obj = to_obj(txt,cik,acn)
        to_tsv(obj)
