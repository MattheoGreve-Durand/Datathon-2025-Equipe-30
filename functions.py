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
        self.new_portefolio = {}


    def getTop10(self, LAW_SUM, investment_horizon):
        #TOP10: {"NAME_ENTREPRISE": {"score": int, "temporiel": float, "score_final": float}}
        self.top_10_entreprises, self.entreprises = getConcernedEntreprises(LAW_SUM, self.ENTREPRISES_KEY, investment_horizon)
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

    def getRiskEffectif(self, ticker):
        return self.getVulnerability(self, ticker)*self.portofolio_dynamic[ticker]/100

    def getRiskEffectifPourcent(self, ticker):
        Rsum = 0 
        for name in self.portofolio_dynamic.keys():
            Rsum += self.getRiskEffectif(self, name)
        return self.getRiskEffectif(self, ticker)/Rsum

    def weight_target(self, ticker):
        top = 1/self.getRiskEffectif(self, ticker)
        Rsum = 0
        for name in self.portofolio_dynamic.keys():
            Rsum += self.getRiskEffectif(self, name)
        bottom = 1/Rsum
        result = top/bottom

        if self.isTargetDeltaCorrect(self, result, ticker):
            return result
        else:
            raise(ValueError("Delta is not correct"))   

    def isTargetDeltaCorrect(self, result, ticker):
        if self.portofolio_dynamic[ticker] - result < 10:
            return True
        else:
            return False
        
    def updatePortefolio(self):
        for ticker in self.portefolio_dynamic.keys():
            try:
                self.new_portefolio[ticker] = self.weight_target(self, ticker)
            except ValueError:
                self.new_portefolio[ticker] = self.portefolio_dynamic[ticker]
        for ticker in self.portefolio_constant.keys():
            self.new_portefolio[ticker] = self.portefolio_constant[ticker]
    

functions = Functions()