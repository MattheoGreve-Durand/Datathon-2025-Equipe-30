import boto3
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import io
from concernedEntreprises.concernedEntreprises import getConcernedEntreprises
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations
from createSpiderCharts.createSpiderCharts import SpiderChart

class Functions:
    def __init__(self):
        self.ENTREPRISES_KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings"
        self.entreprises = {}
        self.top_10_entreprises = {}
        # data structures normalized: each ticker -> {"weight": <num>, ...}
        self.portefolio_constant = {}   # tickers not in top 10
        self.portefolio_dynamic = {}    # tickers in top 10
        self.portefolio = {}            # all tickers combined
        self.spiderCharts = {}
        self.new_portefolio = {}

    # === utilitaire : ensure structure is dict with 'weight' ===
    @staticmethod
    def _ensure_entry_struct(d: dict, ticker: str):
        v = d.get(ticker)
        if isinstance(v, (int, float)):
            d[ticker] = {"weight": float(v)}
        elif isinstance(v, dict) and "weight" not in v:
            # maybe existing dict with other fields: ensure weight key
            d[ticker]["weight"] = float(v.get("weight", 0.0))

    def importPorteFolio(self, json_portefolio: dict):
        """
        Normalize and split the incoming portfolio into dynamic/constant, and
        populate self.portefolio with dict entries {'weight': ...}
        """
        # make sure top_10_entreprises is known (call getTop10 before if needed)
        for ticker, weight in json_portefolio.items():
            entry = {"weight": float(weight)}
            self.portefolio[ticker] = entry
            if ticker in self.top_10_entreprises:
                self.portefolio_dynamic[ticker] = entry.copy()
            else:
                self.portefolio_constant[ticker] = entry.copy()
        return True

    def getTop10(self, LAW_SUM, investment_horizon):
        # TOP10: {"NAME_ENTREPRISE": {"score": int, ...}}
        self.top_10_entreprises, self.entreprises = getConcernedEntreprises(LAW_SUM, self.ENTREPRISES_KEY, investment_horizon)
        return self.top_10_entreprises

    def getSpiderCharts(self, tickers, LAW_SUM):
        for ticker in tickers:
            self.spiderCharts[ticker] = SpiderChart(ticker, LAW_SUM)
        return self.spiderCharts

    def computePositiveImpact(self, array: dict, law_sum, prompt=None):
        """
        array is expected to be a dict mapping ticker -> either {'weight':...} or numeric.
        This function will ensure structure and add keys:
            - spiderChart
            - positiveImpact (float)
        """
        for ticker in list(array.keys()):
            # ensure structure
            self._ensure_entry_struct(array, ticker)

            # create spiderChart if not present
            if "spiderChart" not in array[ticker] or array[ticker]["spiderChart"] is None:
                array[ticker]["spiderChart"] = SpiderChart(ticker, law_sum)

            # obtain prompt if not provided (assuming generate_bedrock_prompt exists somewhere)
            try:
                if prompt is None:
                    # if you have a generator, call it, otherwise pass None
                    from some_module import generate_bedrock_prompt  # replace with real import if exists
                    prompt = generate_bedrock_prompt()
            except Exception:
                prompt = None

            # Call SpiderChart scoring (adapt to actual signature of getSpiderChartScores)
            try:
                # Example: spiderChart.getSpiderChartScores(prompt, law_sum) -> float
                array[ticker]["positiveImpact"] = array[ticker]["spiderChart"].getSpiderChartScores(prompt, law_sum)
            except Exception as e:
                print(f"⚠️ Error computing positiveImpact for {ticker}: {e}")
                array[ticker]["positiveImpact"] = 0.0

    def getVulnerability(self, ticker: str) -> float:
        """
        vulnerability = score_final * (1 - positiveImpact)
        Requires self.entreprises[ticker] to have 'score_final'
        and array entries to have 'positiveImpact'.
        """
        if ticker not in self.entreprises:
            raise KeyError(f"{ticker} not found in entreprises")
        ent = self.entreprises[ticker]
        score_final = float(ent.get("score_final", 0.0))
        # get positiveImpact from portefolio if exists else 0
        pinfo = self.portefolio.get(ticker, {})
        positive = float(pinfo.get("positiveImpact", 0.0))
        return score_final * (1 - positive)

    def getRiskEffectif(self, ticker: str) -> float:
        """
        Effective risk contribution = vulnerability * weight (%) / 100
        Assumes weight stored under 'weight' in portefolio_dynamic.
        """
        if ticker not in self.portefolio_dynamic:
            raise KeyError(f"{ticker} not in dynamic portfolio")
        vuln = self.getVulnerability(ticker)
        weight = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
        return vuln * (weight / 100.0)

    def getRiskEffectifPourcent(self, ticker: str) -> float:
        """
        Returns the share (percent) of this ticker in the total dynamic risk.
        """
        Rsum = 0.0
        for name in self.portefolio_dynamic.keys():
            Rsum += self.getRiskEffectif(name)
        if Rsum == 0:
            return 0.0
        return self.getRiskEffectif(ticker) / Rsum

    def weight_target(self, ticker: str) -> float:
        """
        A target weight calculation based on inverse risk (example).
        Returns a weight in the same percentage scale as the inputs.
        """
        # compute inverse risk per ticker
        inv_risks = {}
        for name in self.portefolio_dynamic.keys():
            re = self.getRiskEffectif(name)
            inv_risks[name] = 1.0 / re if re != 0 else 0.0

        denom = sum(inv_risks.values())
        if denom == 0:
            # fallback: keep the same weight
            return float(self.portefolio_dynamic[ticker].get("weight", 0.0))

        # target weight as normalized inverse-risk (sum to 100)
        target_fraction = inv_risks[ticker] / denom
        return target_fraction * 100.0

    def delta_weight(self, ticker: str) -> float:
        """
        Return target - current (delta).
        """
        target = self.weight_target(ticker)
        current = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
        return target - current

    def isTargetDeltaCorrect(self, result: float, ticker: str, threshold: float = 10.0) -> bool:
        """
        Check if the absolute difference is within threshold percent points.
        """
        current = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
        return abs(current - result) < threshold

    def updatePortefolio(self):
        """
        Create self.new_portefolio by applying target adjustments to dynamic tickers
        while keeping constant tickers unchanged.
        This is a conservative update: if target delta is too large, keep current weight.
        """
        self.new_portefolio = {}
        espace_disponible = 0.0

        # ensure structures are normalized
        for t in list(self.portefolio_dynamic.keys()):
            self._ensure_entry_struct(self.portefolio_dynamic, t)

        for ticker in self.portefolio_dynamic.keys():
            try:
                tgt = self.weight_target(ticker)
                if self.isTargetDeltaCorrect(tgt, ticker):
                    # accept target
                    self.new_portefolio[ticker] = float(tgt)
                else:
                    # too large change -> keep old
                    self.new_portefolio[ticker] = float(self.portefolio_dynamic[ticker]["weight"])
            except Exception as e:
                print(f"⚠️ updatePortefolio error for {ticker}: {e}")
                self.new_portefolio[ticker] = float(self.portefolio_dynamic[ticker].get("weight", 0.0))

        # add constant tickers unchanged
        for ticker in self.portefolio_constant.keys():
            self.new_portefolio[ticker] = float(self.portefolio_constant[ticker]["weight"])

        # compute espace disponible to make the total sum to 100 if needed
        total = sum(self.new_portefolio.values())
        if total < 100:
            espace_disponible = 100.0 - total
            self.new_portefolio["Espace Disponible"] = espace_disponible
        else:
            # optional: normalize to 100 or leave as is; here we keep as is and set espace to 0
            self.new_portefolio["Espace Disponible"] = 0.0

        return self.new_portefolio

    def plot_portfolio_comparison(self, title: str = "Comparaison des portefeuilles"):
        """
        Returns a PIL.Image with two pie charts comparing self.portefolio and self.new_portefolio.
        """
        if not self.portefolio or not self.new_portefolio:
            raise ValueError("One of the portfolios is empty.")

        # extract labels and numeric values
        old_labels = list(self.portefolio.keys())
        old_values = [float(self.portefolio[k].get("weight", 0.0)) if isinstance(self.portefolio[k], dict)
                      else float(self.portefolio[k]) for k in old_labels]

        new_labels = list(self.new_portefolio.keys())
        new_values = [float(self.new_portefolio[k]) if not isinstance(self.new_portefolio[k], dict)
                      else float(self.new_portefolio[k].get("weight", 0.0)) for k in new_labels]

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].pie(old_values, labels=old_labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
        axes[0].set_title("Ancien portefeuille", fontsize=14, fontweight='bold')

        axes[1].pie(new_values, labels=new_labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
        axes[1].set_title("Nouveau portefeuille", fontsize=14, fontweight='bold')

        plt.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        image = Image.open(buf).convert("RGBA")
        buf.close()
        return image
    

if __name__ == "__main__":
    BUCKET = "csv-file-store-ec51f700"
    LAW_KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html"

    functions = Functions()
    # importer un portefeuille initial
    functions.importPorteFolio({
        "AAPL": 25, "MSFT": 25, "GOOGL": 10, "AMZN": 10, "TSLA": 5,
        "META": 5, "NVDA": 5, "PEP": 5, "COST": 5, "AVGO": 5
    })

    # récupérer le texte du fichier S3
    s3 = boto3.client("s3")
    law_content = s3.get_object(Bucket=BUCKET, Key=LAW_KEY)["Body"]
    SUM_LAW = getLawInformations(law_content)

    # top10 entreprises
    functions.getTop10(SUM_LAW, "Court terme")

    print("COMPUTING: ...")
    functions.computePositiveImpact(functions.portefolio, SUM_LAW)

    print("Portefeuille enrichi:", functions.portefolio)
    functions.updatePortefolio()
    print("Nouveau portefeuille:", functions.new_portefolio)

    print("drawing...")
    img = functions.plot_portfolio_comparison()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)  # revenir au début du buffer

    # Upload vers S3
    s3 = boto3.client("s3")
    BUCKET = "csv-file-store-ec51f700"
    KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/Camenbert/new_portefolio"  # chemin et nom dans le bucket

    s3.put_object(
        Bucket=BUCKET,
        Key=KEY,
        Body=buffer.getvalue(),
        ContentType="image/png"
    )

    buffer.close()
    print(f"✅ New portfolio image uploaded to s3://{BUCKET}/{KEY}")

functions = Functions()