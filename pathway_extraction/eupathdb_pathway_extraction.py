#!/usr/bin/env python3

import csv
import re
import requests

from tqdm import tqdm

from . import *

def request_database_eupathdb(db_database, session=requests):
    '''
        Requests all the databases present in EuPathDB.
        The requests retrieve all the file names which are present in the pathwayFiles folder of the download part of the database.
        File names are stored in a dictionnary.
    '''
    db_database_pathways = {}
    metacyc_pathways = []
    kegg_pathways = []

    r = session.get('http://' + db_database + '.org/common/downloads/pathwayFiles//MetaCyc/')
    for row in r.text.split("\n"):
        if '<img src="/icons/unknown.gif" alt="[   ]"> <a href=' in row:
            metacyc_pathways.append(row[len('<img src="/icons/unknown.gif" alt="[   ]"> <a href="'):].split('"')[0])

    r = session.get('http://' + db_database + '.org/common/downloads/pathwayFiles//KEGG/')
    for row in r.text.split("\n"):
        if '<img src="/icons/unknown.gif" alt="[   ]"> <a href=' in row:
            kegg_pathways.append(row[len('<img src="/icons/unknown.gif" alt="[   ]"> <a href="'):].split('"')[0])

    if db_database == 'tritrypdb':
        leishcyc_pathways = []
        trypanocyc_pathways = []
        r = session.get('http://' + db_database + '.org/common/downloads/pathwayFiles//LeishCyc/')
        for row in r.text.split("\n"):
            if '<img src="/icons/unknown.gif" alt="[   ]"> <a href=' in row:
                leishcyc_pathways.append(row[len('<img src="/icons/unknown.gif" alt="[   ]"> <a href="'):].split('"')[0])

        r = requests.get('http://' + db_database + '.org/common/downloads/pathwayFiles//TrypanoCyc/')
        for row in r.text.split("\n"):
            if '<img src="/icons/unknown.gif" alt="[   ]"> <a href=' in row:
                trypanocyc_pathways.append(row[len('<img src="/icons/unknown.gif" alt="[   ]"> <a href="'):].split('"')[0])

        db_database_pathways['LeishCyc'] = leishcyc_pathways
        db_database_pathways['TrypanoCyc'] = trypanocyc_pathways

    db_database_pathways['MetaCyc'] = metacyc_pathways
    db_database_pathways['KEGG'] = kegg_pathways

    return db_database_pathways

def request_and_parse_pathway_file(db_database, database, pathways_file_name, session=requests):
    '''
        Use the dictionnary containing all of the file names from a database.
        For each file name a request is sent to EuPathDB to retrieve the file.
        Then the file is parsed and the association between ID (ChEBI and Enzyme code) and pathway (MetaCyc, KEGG) are extracted and writed into a csv.
    '''
    csvfile = open(temporary_directory_database + "ecChebiToPathway_" + db_database + database + ".tsv", "w", newline="")
    writer = csv.writer(csvfile, delimiter="\t")
    writer.writerow(('pathway', 'ecChebis'))

    label_node_pathec = r'[\w\d\s\,\/\;\&\(\)\[\]-]{6,}'
    label_node_rxn = r'RXN-[\d]{1}'
    label_node_chebi = r'C[\d]{5}'
    label_node_pathec_check = False
    label_node_chebi_check = False

    for pathway_file_name in pathways_file_name:
        if '.xgmml' in pathway_file_name:
            r = session.get('http://' + db_database + '.org/common/downloads/pathwayFiles//' + database + '/' + pathway_file_name)

            pathway = pathway_file_name[:-len('.xgmml')]

            for row in r.text.split("\n"):
                if "node label" in row:
                    label = row[len('  <node label="'):].split('"')[0]

                    if re.match(label_node_chebi, label):
                        label_node_chebi_check = True
                    elif re.match(label_node_pathec, label) or re.match(label_node_rxn, label):
                        label_node_pathec_check = True
                    else:
                        ec_chebi = label
                        writer.writerow((pathway, ec_chebi))
                        label_node_pathec_check = False
                        label_node_chebi_check = False
                if '    <att name=Description" value=' in row and label_sentence_check == True:
                    ec_chebi = row[len('    <att name=Description" value="'):].split('"')[0]
                    writer.writerow((pathway, ec_chebi))
                if '    <att name="CID" value=' in row and label_node_chebi_check == True:
                    ec_chebi = row[len('    <att name="CID" value="'):].split('"')[0]
                    writer.writerow((pathway, ec_chebi))

    csvfile.close()

def main(session=requests):
    db_databases = ['amoebadb', 'cryptodb', 'fungidb', 'giardiadb', 'microsporidiadb', 'piroplasmadb', 'plasmodb', 'toxodb', 'trichdb', 'tritrypdb']

    for db_database in tqdm(db_databases):
        db_database_pathways = request_database_eupathdb(db_database, session)
        request_and_parse_pathway_file(db_database, 'KEGG', db_database_pathways['KEGG'], session)
        request_and_parse_pathway_file(db_database, 'MetaCyc', db_database_pathways['MetaCyc'], session)
        if db_database == 'tritrypdb':
            request_and_parse_pathway_file(db_database, 'LeishCyc', db_database_pathways['LeishCyc'], session)
            request_and_parse_pathway_file(db_database, 'TrypanoCyc', db_database_pathways['TrypanoCyc'], session)
