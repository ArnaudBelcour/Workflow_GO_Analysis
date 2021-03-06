#!/usr/bin/env python3

import logging
import numpy as np
import os
import pandas as pa
import re
import requests
import subprocess

import mapping_pathway_data
import pathway_extraction.chebi_from_go as chebi_from_go
import pathway_extraction.database_mapping_from_gos as database_mapping_from_gos
import pathway_extraction.eupathdb_pathway_extraction as eupathdb_pathway_extraction
import pathway_extraction.ghost_koala_pathway_extraction as ghost_koala_pathway_extraction
import pathway_extraction.interpro_pathway_extraction as interpro_pathway_extraction
import pathway_extraction.panther_pathway_mapping_uniprot as panther_pathway_mapping_uniprot
import pathway_extraction.reactome_pathway_extraction as reactome_pathway_extraction
import pathway_extraction.sparql_query_reactome_pathway_name as sparql_query_reactome_pathway_name

temporary_directory = 'temporaryFiles/'
temporary_directory_database = 'temporaryFiles/databases/'

logging.basicConfig(filename='analysis.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

def ec_extraction(df_genome):
    ecs_requests = []

    for ecs in df_genome['EnzymeCodes']:
        for ec in ecs.lower().split(","):
            if ec not in ecs_requests and ec != '':
                ecs_requests.append(ec)

    return ecs_requests

def r_keggrest_ec(ecs_requests):
    '''
        Uses the R script to extract pathway using Enzyme Code in KEGG.
        Show the progress bar send by R in the console (and update it during the iteration).
    '''
    command = 'Rscript'
    path_script = 'pathway_extraction/keggrest_pathway_extraction.R'
    data_name = ["enzyme"]
    cmd = [command, path_script] + ecs_requests + data_name

    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        if "%" in stdout_line:
            print ("\x1b[2K\r{}".format(stdout_line.rstrip()), end="")
    print("\r")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def mapping_data(file_name, df_genome):
    df_mapping = pa.read_csv(temporary_directory_database + file_name, sep='\t')

    df_mapping['GOs'] = df_mapping['GOs'].str.replace("_", ":")
    df_mapping = df_mapping.set_index("GOs")
    data_column = df_mapping.columns[0]
    df_genome[data_column] = df_genome['GOs'].apply(mapping_pathway_data.translation_data, args = (df_mapping, data_column, 'initial'))

    return df_genome

def data_retrieval_from_GO(file_name_temporary):
    '''
        Add Interpro and Enzyems Codes found with mapping files of the Gene Ontology.
        Add ChEBI linked with GO terms.
    '''
    logger.info('-------------------------------------Data retrieval from GO-------------------------------------')
    df_genome = pa.read_csv(temporary_directory + file_name_temporary, sep="\t")
    df_genome.replace(np.nan, '', regex=True, inplace=True)

    print("GO mapping files interrogation")
    database_mapping_from_gos.main()

    print("GO owl interrogation to retrieve ChEBI")
    chebi_from_go.go_to_chebi()

    for file_name in os.listdir(temporary_directory_database):
        if "mapping" in file_name:
            df_genome = mapping_data(file_name, df_genome)

    for index, row in df_genome.iterrows():
        if row['EnzymeCodes'] == '':
            df_genome.set_value(index, 'EnzymeCodes', row['ec_code'])
        if row['InterProScan'] == '':
            df_genome.set_value(index, 'InterProScan', row['interpro'])

    df_genome.drop('ec_code', 1, inplace=True)
    df_genome.drop('interpro', 1, inplace=True)

    logger.debug('df_genome: %s', df_genome)

    df_genome.to_csv(temporary_directory + file_name_temporary, sep='\t', index=False)

def main(file_name_temporary, session=requests):
    logger.info('-------------------------------------Pathway extractor main-------------------------------------')
    df_genome = pa.read_csv(temporary_directory + file_name_temporary, sep='\t')
    df_genome.replace(np.nan, '', regex=True, inplace=True)

    print("Keggrest interrogation")
    ecs_requests = ec_extraction(df_genome)
    r_keggrest_ec(ecs_requests)

    print("EupathDB interrogation")
    eupathdb_pathway_extraction.main(session)

    print("Ghost Koala interrogation")
    ghost_koala_pathway_extraction.main()

    print("Interpro interrogation")
    interpro_pathway_extraction.request_interpro_pathway()

    print("Panther interrogation")
    panther_pathway_mapping_uniprot.request_panther_file()

    print("Reactome interrogation")
    reactome_pathway_extraction.main(file_name_temporary, session)

    print("Reactome endpoint interrogation")
    sparql_query_reactome_pathway_name.main()
