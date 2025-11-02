import boto3
from concernedEntreprises.concernedEntreprises import getConcernedEntreprises
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations
from createSpiderCharts.createSpiderCharts import SpiderChart

class Functions:
    def __init__(self):
        self.ENTREPRISES_KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings"
        self.entreprises = {}
        self.top_10_entreprises = {}
        self.portefolio_constant = {}
        self.portefolio_dynamic = {}
        self.spiderGraphs = {}

    def getTop10(self, LAW_SUM, investment_horizon):
        #TOP10: {"NAME_ENTREPRISE": {"score": int, "temporiel": float, "score_final": float}}
        self.top_10_entreprises, self.entreprises = getConcernedEntreprises(LAW_SUM, self.ENTREPRISES_KEY, investment_horizon)


        print("DEBUG: TOP 10 ENTREPRISES: ", self.top_10_entreprises)
        return self.top_10_entreprises


    def importPorteFolio(self, json_portefolio):
        #PORTEFOLIO: {"NAME_ENTREPRISE":Weight, "NAME_ENTREPRISE":Weight}
        for ticker in json_portefolio.keys():
            if ticker in self.top_10_entreprises.keys():
                self.portefolio_dynamic[ticker] = json_portefolio[ticker]
            else:
                self.portefolio_constant[ticker] = json_portefolio[ticker]
        return True

    def computePositiveImpact(self, array):
        for ticker in array.keys():
            array[ticker]["spiderGraph"] = SpiderGraph(ticker)
            array[ticker]["positiveImpact"] = array[ticker]["spiderGraph"].getSpiderChartScores(generate_bedrock_prompt(), SUM_LAW)
    

    def getVulnerability(self, ticker):
        ticker_entreprise = self.entreprises[ticker]
        return ticker_entreprise["score_final"]*(1-ticker_entreprise["positiveImpact"])


functions = Functions()