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
        self.portefolio = {} 
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
            self.portefolio[ticker] = json_portefolio[ticker]
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
        return top/bottom

    def delta_weigth(self, ticker):
        if self.isTargetDeltaCorrect(self, weight_target(self, ticker), ticker):
            return self.weight_target(self, ticker) - self.portofolio_dynamic[ticker]
        else:
            raise(ValueError("Delta is not correct"))

    def isTargetDeltaCorrect(self, result, ticker):
        if abs(self.portofolio_dynamic[ticker] - result) < 10:
            return True
        else:
            return False
        
    def updatePortefolio(self):
        espace_disponible = 0
        for ticker in self.portefolio_dynamic.keys():
            try:
                if self.delta_weight(self, ticker):
                    self.new_portefolio[ticker] = 10
            except ValueError:
                self.new_portefolio[ticker] = self.portefolio_dynamic[ticker]
        for ticker in self.portefolio_constant.keys():
            self.new_portefolio[ticker] = self.portefolio_constant[ticker]
        self.new_portefolio["Espace Disponible"]  = espace_disponible
    
    def plot_portfolio_comparison(self):

        # === 1. Récupérer les données ===
        old_data = self.portfolio
        new_data = self.new_portfolio

        # Vérifier que les deux dicts ne sont pas vides
        if not old_data or not new_data:
            raise ValueError("One of the portfolios is empty.")

        # === 2. Préparer les labels et les valeurs ===
        old_labels = list(old_data.keys())
        old_values = list(old_data.values())

        new_labels = list(new_data.keys())
        new_values = list(new_data.values())

        # === 3. Création de la figure ===
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))

        # === 4. Premier camembert (ancien portefeuille) ===
        axes[0].pie(
            old_values,
            labels=old_labels,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10},
            colors=plt.cm.Paired.colors
        )
        axes[0].set_title("Ancien portefeuille", fontsize=14, fontweight='bold')

        # === 5. Deuxième camembert (nouveau portefeuille) ===
        axes[1].pie(
            new_values,
            labels=new_labels,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10},
            colors=plt.cm.Paired.colors
        )
        axes[1].set_title("Nouveau portefeuille", fontsize=14, fontweight='bold')

        # === 6. Ajuster la mise en page ===
        plt.suptitle(f"Comparaison des portefeuilles ({self.ticker})", fontsize=16, fontweight='bold')
        plt.tight_layout()

        # === 7. Sauvegarder dans un buffer mémoire ===
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)  # fermer proprement la figure
        buffer.seek(0)

        # === 8. Convertir en objet PIL.Image ===
        image = Image.open(buffer).convert("RGBA")
        buffer.close()

        # Retourner l’image PIL
        return image



functions = Functions()