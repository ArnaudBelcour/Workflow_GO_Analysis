#!/usr/bin/env python3

import csv
import urllib.request

from gzip import GzipFile
from lxml import etree
from tqdm import tqdm

from . import *

def request_interpro_pathway():
    '''
        Requests Interpro to retrieve the interpro.xml.gz file.
        The file is analyzed and the Interpro ID are extracted with their associated pathways.
    '''
    url = 'ftp://ftp.ebi.ac.uk/pub/databases/interpro/interpro.xml.gz'
    file_name = 'interpro'
    response = urllib.request.urlopen(url)

    csvfile = open(temporary_directory_database + "interpro_pathway.tsv", "w")
    writer = csv.writer(csvfile, delimiter='\t')
    writer.writerow(['Interpros', 'Database', 'Pathway_id'])

    with GzipFile(fileobj = response) as xmlFile:
        coords = etree.parse(xmlFile).getroot()

        for coord in tqdm(coords):
            interpro_id = coord.attrib.get('id')
            if interpro_id is not None:
                for childs in coord.getchildren():
                    for child in childs:
                        database_name = child.attrib.get('db')
                        if database_name in ["KEGG", "REACTOME", "METACYC"]:
                            pathway_id = child.attrib['dbkey']
                            if database_name == "KEGG":
                               pathway_id = pathway_id.split("+")[0]
                            writer.writerow([interpro_id, database_name, pathway_id])

    csvfile.close()
