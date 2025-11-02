import boto3
from concernedEntreprises.concernedEntreprises import getConcernedEntreprises
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations
from createSpiderCharts.createSpiderCharts import SpiderChart

def getTop10(LAW_SUM):

    ENTREPRISES_KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings"
    top_10_entreprises = getConcernedEntreprises(LAW_SUM, ENTREPRISES_KEY)

    print("DEBUG: TOP 10 ENTREPRISES: ", top_10_entreprises)
    return top_10_entreprises
