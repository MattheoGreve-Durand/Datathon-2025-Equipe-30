import sys
import os
import boto3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pydantic import BaseModel
import instructor
import io

sys.path.insert(0, '/home/sagemaker-user/shared')

from dataExtractionFrom10K.dataExtractionNumerical10K import getNumericalFrom10K
from dataExtractionFromYahoo.dataExtractionFromYahoo import get_financial_data
from dataExtractionFrom10K.tableExtractionFrom10K import extract_only_tables
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations

class SpiderChartScore(BaseModel):
    PROFITABILITY_SCORE: int
    GROWTH_SCORE: int
    STABILITY_SCORE: int
    MARKET_SCORE: int
    EFFICIENCY_SCORE: int
    CAPITAL_COST_SCORE: int



class SpiderChart:
    def __init__(self, ticker):
        self.ticker = ticker
        s3 = boto3.client("s3")

        self.BUCKET = "csv-file-store-ec51f700"
        self.prefix = f"dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings/{ticker}/"
        self.image_prefix =  f"dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data"
        self.law_key = f"dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html"
        
        self.text_of_law =  getLawInformations(self.BUCKET, self.law_key)

        result = s3.list_objects_v2(Bucket=self.BUCKET, Prefix=self.prefix)

        html_files = [item["Key"] for item in result.get("Contents", []) if item["Key"].endswith(".html")]

        if not html_files:
            raise FileNotFoundError(f"Aucun fichier HTML trouvé pour {ticker} dans {self.prefix}")

        html_key = html_files[0]
        obj = s3.get_object(Bucket=self.BUCKET, Key=html_key)
        html_content = obj["Body"].read().decode("utf-8")
        #print(html_content)

        print("DEBUG: Getting all the data...")
        self.numerical_data = getNumericalFrom10K(extract_only_tables(html_content))

        print(f"DEBUG: {self.numerical_data}")
        # Data from 10K
        self.net_income = self.numerical_data.net_income
        self.revenue = self.numerical_data.revenue
        self.preferred_dividend = self.numerical_data.preferred_dividend
        self.average_of_CS = self.numerical_data.average_of_CS
        self.she = self.numerical_data.she  # Shareholders' Equity
        self.total_asset = self.numerical_data.total_asset
        self.eps_current = self.numerical_data.eps_current
        self.eps_previous = self.numerical_data.eps_previous
        self.revenue_current = self.numerical_data.revenue_current
        self.revenue_previous = self.numerical_data.revenue_previous
        self.asset_current = self.numerical_data.asset_current
        self.liabilities_current = self.numerical_data.liabilities_current
        self.total_debt = self.numerical_data.total_debt
        self.operating_income = self.numerical_data.operating_income
        self.cost_of_good_sold = self.numerical_data.cost_of_good_sold
        self.inventory_avg = self.numerical_data.inventory_avg
        self.cost_of_debt = self.numerical_data.cost_of_debt
        self.corporate_tax_rate = self.numerical_data.corporate_tax_rate

        # Data from yahoo finance
        self.yahoo_data = get_financial_data(self.ticker)
        self.share_price = self.yahoo_data["sharePrice"]
        self.eps = self.yahoo_data["eps"]
        self.stock_return = self.yahoo_data["stockReturn"] 
        self.market_return = self.yahoo_data["marketReturn"]
        self.cost_of_equity = self.yahoo_data["Capm"]
        self.beta = self.yahoo_data["beta"]
        self.risk_free_rate = self.yahoo_data["riskFreeRate"]
        self.market_return = self.yahoo_data["rm"]
        self.sentiment_score = self.yahoo_data["recommendationMean"]

        # Calculated data
        self.market_value_equity = self.share_price * self.average_of_CS
        self.market_value_debt = self.total_debt
        self.total_market_value = self.market_value_equity+self.market_value_debt

        self.PROFITABILITY_SCORE = 0
        self.GROWTH_SCORE = 0
        self.STABILITY_SCORE = 0
        self.MARKET_SCORE = 0
        self.EFFICIENCY_SCORE = 0
        self.CAPITAL_COST_SCORE = 0


        # ============================================================
        # === 1. PROFITABILITY                                     ===
        # ============================================================
        try:
            self.net_profit_margin = (self.net_income / self.revenue) * 100
        except ZeroDivisionError:
            self.net_profit_margin = None

        try:
            self.earning_per_share = (self.net_income - self.preferred_dividend) / self.average_of_CS
        except ZeroDivisionError:
            self.earning_per_share = None

        try:
            self.return_on_equity = self.net_income / self.she
        except ZeroDivisionError:
            self.return_on_equity = None

        try:
            self.return_on_assets = self.net_income / self.total_asset
        except ZeroDivisionError:
            self.return_on_assets = None

        # ============================================================
        # === 2. GROWTH POTENTIAL ===
        # ============================================================
        try:
            self.eps_growth_rate = (self.eps_current - self.eps_previous) / self.eps_previous
        except ZeroDivisionError:
            self.eps_growth_rate = None

        try:
            self.revenue_growth_rate = (self.revenue_current - self.revenue_previous) / self.revenue_previous
        except ZeroDivisionError:
            self.revenue_growth_rate = None

        # ============================================================
        # === 3. FINANCIAL STABILITY ===
        # ============================================================
        try:
            self.current_ratio = self.asset_current / self.liabilities_current
        except ZeroDivisionError:
            self.current_ratio = None

        try:
            self.debt_to_equity = self.total_debt / self.she
        except ZeroDivisionError:
            self.debt_to_equity = None

        # Inversion pour Debt/Equity (moins de dette = meilleur score)
        debt_to_equity_inverted = 1 / self.debt_to_equity if self.debt_to_equity and self.debt_to_equity != 0 else 0


        # ============================================================
        # === 4. MARKET PERCEPTION ===
        # ============================================================
        try:
            self.pe_ratio = self.share_price / self.eps if self.eps else None
        except ZeroDivisionError:
            self.pe_ratio = None

        # Inversion du P/E et du Beta : plus bas = meilleur
        self.pe_inverted = 1 / self.pe_ratio if self.pe_ratio and self.pe_ratio != 0 else 0
        self.beta_inverted = 1 / self.beta if self.beta and self.beta != 0 else 0

        # Sentiment analysis placeholder (entre -1 et 1)

        # ============================================================
        # === 5. OPERATIONAL EFFICIENCY ===
        # ============================================================
        try:
            self.operating_margin = self.operating_income / self.revenue
        except ZeroDivisionError:
            self.operating_margin = None

        try:
            self.inventory_turnover = self.cost_of_good_sold / self.inventory_avg
        except ZeroDivisionError:
            self.inventory_turnover = None

        try:
            self.asset_turnover = self.revenue / self.total_asset
        except ZeroDivisionError:
            self.asset_turnover = None


        # ============================================================
        # === 6. CAPITAL COST ===
        # ============================================================
        cost_of_equity = self.cost_of_equity or 0
        cost_of_debt = self.cost_of_debt or 0

    def generate_bedrock_prompt(self):
        prompt = f"""
            CONTEXTE
            Tu es un système d'analyse financière qui évalue l'impact potentiel d'une nouvelle loi sur la performance boursière d'une entreprise. Tu dois analyser 6 critères principaux.
            Ne va pas sur internet et surtout n'invente pas de donnee.
            CRITÈRES D'ANALYSE ET LEURS INDICATEURS
            1. PROFITABILITY (Rentabilité)
            Indicateurs:

            Net Profit Margin (poids: 25%)
            EPS - Earnings Per Share (poids: 35%)
            ROE - Return on Equity (poids: 25%)
            ROA - Return on Assets (poids: 15%)
            Règle d'impact: Si les valeurs augmentent → impact positif | Si diminuent → impact négatif

            2. GROWTH POTENTIAL (Potentiel de Croissance)
            Indicateurs:

            EPS Growth Rate (poids: 50%)
            Revenue Growth Rate (poids: 50%)
            Règle d'impact: Croissance élevée → impact positif | Croissance faible → impact négatif

            3. FINANCIAL STABILITY (Stabilité Financière)
            Indicateurs:

            Current Ratio (poids: 50%) - Plus élevé = meilleur
            Debt-to-Equity Ratio (poids: 50%) - Plus bas = meilleur
            Règle d'impact: Current Ratio ↑ et Debt-to-Equity ↓ → impact positif

            4. MARKET PERCEPTION (Perception du Marché)
            Indicateurs:

            P/E Ratio (poids: 30%) - Modéré = meilleur
            Stock Beta (poids: 30%) - Plus bas = moins risqué
            Sentiment Score (poids: 40%) - Score de -1 à +1
            Règle d'impact: Sentiment positif et volatilité faible → impact positif

            5. OPERATIONAL EFFICIENCY (Efficacité Opérationnelle)
            Indicateurs:

            Operating Margin (poids: 40%)
            Inventory Turnover (poids: 30%)
            Asset Turnover (poids: 30%)
            Règle d'impact: Valeurs élevées → meilleure efficacité → impact positif

            6. CAPITAL COST (Coût du Capital)
            Indicateurs:

            WACC (poids: 60%) - Plus bas = meilleur
            Cost of Equity (poids: 40%) - Plus bas = meilleur
            Règle d'impact: Coûts faibles → impact positif | Coûts élevés → impact négatif

            INSTRUCTIONS D'ANALYSE
            ENTRÉE: Reçois les données financières de l'entreprise et la description de la nouvelle loi

            CALCUL DES SCORES:

            Pour chaque critère, calcule un score pondéré (0-100) basé sur ses indicateurs
            Score_Critère = Σ(Indicateur_normalisé × Poids_indicateur)
            
            ANALYSE D'IMPACT SUR LES SCORES:

            Estime comment la loi affectera chaque indicateur
            Recalcule les scores projetés après application de la loi

            CLASSIFICATION DE L'IMPACT:

            Impact très positif: variation > +20%
            Impact positif: variation entre +5% et +20%
            Impact neutre: variation entre -5% et +5%
            Impact négatif: variation entre -20% et -5%
            Impact très négatif: variation < -20%

            OUTPUT:
            Score des 6 domaines
            EXEMPLE D'UTILISATION
            Input:
            Output attendu:

            Analyse détaillée:
            "La loi [X] aura un impact [classification]"
            "Profitability: "
            [Répéter pour les 6 critères]
            Recommandation finale basée sur l'impact global
            PRINCIPE DE PROPORTIONNALITÉ
            Chaque variation d'indicateur affecte proportionnellement son critère parent. L'impact global est la moyenne pondérée de tous les critères, avec possibilité d'ajuster les poids selon le secteur d'activité.
                """
        return prompt

    def getSpiderChartScores(self, prompt, law):
        #print("DEBUG: Law resume: ", law)
        bedrock_client = boto3.client('bedrock-runtime')
        client = instructor.from_bedrock(bedrock_client)
        print("DEBUG: Sending prompte, awaiting response...")
        response = client.chat.completions.create(
            modelId= "anthropic.claude-3-sonnet-20240229-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": (f"{prompt}\n"
                                "f{}\n"
                                f"{law}"
                    ),
                },
            ],
            response_model=SpiderChartScore,
            inferenceConfig={
                "maxTokens": 4096,
            }
        )
        return response


    def drawHexagonRadar(self):

        labels = [
            "Profitability",
            "Growth \nPotential",
            "Financial \nStability",
            "Market \nPerception",
            "Operational \nEfficiency",
            "Capital Cost"
        ]

        print("DEBUG: Getting Scores")
        print("DEBUG: Prompt: ", self.generate_bedrock_prompt())
        score = self.getSpiderChartScores(self.generate_bedrock_prompt(), self.text_of_law)
        
        self.PROFITABILITY_SCORE = score.PROFITABILITY_SCORE
        self.GROWTH_SCORE = score.GROWTH_SCORE
        self.STABILITY_SCORE = score.STABILITY_SCORE
        self.MARKET_SCORE = score.MARKET_SCORE
        self.EFFICIENCY_SCORE = score.EFFICIENCY_SCORE
        self.CAPITAL_COST_SCORE = score.CAPITAL_COST_SCORE

        values = [
            self.PROFITABILITY_SCORE,
            self.GROWTH_SCORE,
            self.STABILITY_SCORE,
            self.MARKET_SCORE,
            self.EFFICIENCY_SCORE,
            self.CAPITAL_COST_SCORE
        ]

        print("DEBUG: Values:", values)
        print("DEBUG: Drawing...")

        # === 1. Fermer le polygone (revenir au début) ===
        values += values[:1]

        # === 2. Angles du graphique ===
        angles = np.linspace(0, 2 * np.pi, len(labels) + 1, endpoint=True)

        # === 3. Création du radar ===
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

        # Tracé du polygone principal
        ax.plot(angles, values, linewidth=2, linestyle='solid', color='dodgerblue')
        ax.fill(angles, values, alpha=0.25, color='dodgerblue')

        # === 4. Réglages du graphique ===
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=12, fontweight='bold')

        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], color='gray', size=10)
        ax.set_ylim(0, 100)

        ax.set_title(f"({self.ticker}) Performance Radar Chart (Hexagon)", size=14, weight='bold', pad=30)
        ax.grid(True)

        # === 🌟 Transformer le fond circulaire en hexagone ===
        # On crée un polygone à 6 côtés (un hexagone) pour le fond
    

        # === 5. Sauvegarde et upload S3 ===
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()

        buffer.seek(0)

        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=self.BUCKET,
            Key=f"{self.image_prefix}/{self.ticker}",
            Body=buffer.getvalue(),
            ContentType="image/png"
        )

        print(f"DEBUG: Radar chart uploaded to s3://{self.BUCKET}/{self.image_prefix}")
        buffer.close()

if __name__ == "__main__":
    apple = SpiderChart("COST")
    apple.drawHexagonRadar()


        




