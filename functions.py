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
        self.espace_disponible = 0

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
                print("portefolio added to dynamic")
            else:
                self.portefolio_constant[ticker] = entry.copy()
        return True

    def getTop10(self, LAW_SUM, investment_horizon):
        # TOP10: {"NAME_ENTREPRISE": {"score": int, ...}}
        self.top_10_entreprises, self.entreprises = getConcernedEntreprises(LAW_SUM, self.ENTREPRISES_KEY, investment_horizon)
        return self.top_10_entreprises

    def getSpiderCharts(self, tickers, LAW_SUM):
        for ticker in tickers:
            self.spiderCharts[ticker] = SpiderChart(ticker, LAW_SUM).drawHexagonRadar()
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
        return vuln * (1-(weight / 100.0))

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
        print("weigth target ", target_fraction * 100.0)
        return target_fraction * 100.0

    def delta_weight(self, ticker: str) -> float:
        """
        Return target - current (delta).
        """
        target = self.weight_target(ticker)
        current = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
        return target - current

    def isTargetDeltaCorrect(self, result: float, ticker: str, threshold: float = 5) -> bool:
        """
        Check if the absolute difference is within threshold percent points.
        """
        current = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
        return abs(current - result) < threshold

    def updatePortefolio(self, max_delta: float = 5.0):
        """
        Update self.new_portefolio based on target weights.
        - If delta_weight exceeds max_delta %, clip the change to max_delta.
        - The excess weight goes into 'Espace Disponible'.
        """
        self.new_portefolio = {}
        self.espace_disponible = 0.0

        # Normaliser toutes les entrées dynamiques
        for t in list(self.portefolio_dynamic.keys()):
            self._ensure_entry_struct(self.portefolio_dynamic, t)

        # Calcul des nouveaux poids pour les tickers dynamiques
        for ticker in self.portefolio_dynamic.keys():
            try:
                current = float(self.portefolio_dynamic[ticker].get("weight", 0.0))
                target = self.weight_target(ticker)
                delta = target - current
                print(f"[DEBUG] {ticker}: current={current}, target={target:.2f}, delta={delta:.2f}")

                if abs(delta) <= max_delta:
                    # accept target
                    self.new_portefolio[ticker] = target
                else:
                    # clip delta to max_delta
                    clipped_delta = max_delta if delta > 0 else -max_delta
                    self.new_portefolio[ticker] = current + clipped_delta
                    self.espace_disponible += abs(delta) - abs(clipped_delta)
                    print(f"[DEBUG] {ticker}: clipped to {self.new_portefolio[ticker]:.2f}, excess -> Espace Disponible={self.espace_disponible:.2f}")

            except Exception as e:
                print(f"⚠️ updatePortefolio error for {ticker}: {e}")
                self.new_portefolio[ticker] = current

        # Ajouter les tickers constants inchangés
        for ticker in self.portefolio_constant.keys():
            self._ensure_entry_struct(self.portefolio_constant, ticker)
            self.new_portefolio[ticker] = float(self.portefolio_constant[ticker].get("weight", 0.0))

        # Ajouter l'espace disponible
        self.new_portefolio["Espace Disponible"] = self.espace_disponible if self.espace_disponible > 0 else 0.0

        print(f"[INFO] Nouveau portefeuille calculé: {self.new_portefolio}")
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

    def suggestStocks(self, top_n: int = 5, bucket: str = None, base_path: str = None):
        """
        Suggest stocks to buy based on top 10 and current portfolio.
        Only suggest tickers not already in the portfolio.
        Cross-check sectors from JSON files in S3 automatically detecting JSON filename.

        Args:
            top_n (int): number of stocks to suggest.
            bucket (str): S3 bucket name.
            base_path (str): S3 path prefix where each ticker folder contains JSON file with "secteurs".

        Returns:
            List of suggested tickers (up to top_n)
            Dict mapping ticker -> secteurs
            Dict of shared sectors among suggested tickers
        """
        if bucket is None or base_path is None:
            raise ValueError("bucket and base_path must be provided")

        # 1️⃣ Top 10 tickers not already in portfolio
        available_top = [t for t in self.top_10_entreprises if t not in self.portefolio]
        suggested = available_top[:top_n]

        s3 = boto3.client("s3")
        ticker_sectors = {}

        # 2️⃣ Fetch sectors for each suggested ticker
        for ticker in suggested:
            folder_prefix = f"{base_path}/{ticker}"
            try:
                response = s3.list_objects_v2(Bucket=bucket, Prefix=folder_prefix)
                if "Contents" not in response or len(response["Contents"]) == 0:
                    print(f"⚠️ No files found in {folder_prefix}")
                    ticker_sectors[ticker] = []
                    continue

                # Find the first JSON file
                json_key = next((obj["Key"] for obj in response["Contents"] if obj["Key"].lower().endswith(".json")), None)
                if json_key is None:
                    print(f"⚠️ No JSON file found for {ticker} in {folder_prefix}")
                    ticker_sectors[ticker] = []
                    continue

                # Read JSON content
                obj = s3.get_object(Bucket=bucket, Key=json_key)
                data = json.loads(obj["Body"].read().decode("utf-8"))
                secteurs = data.get("secteurs", [])
                ticker_sectors[ticker] = secteurs

            except Exception as e:
                print(f"⚠️ Could not fetch secteurs for {ticker}: {e}")
                ticker_sectors[ticker] = []

        # 3️⃣ Detect shared sectors
        shared_sectors = {}
        all_sectors = {}
        for ticker, secteurs in ticker_sectors.items():
            for secteur in secteurs:
                all_sectors.setdefault(secteur, []).append(ticker)

        for secteur, tickers in all_sectors.items():
            if len(tickers) > 1:
                shared_sectors[secteur] = tickers

        return suggested, ticker_sectors, shared_sectors


if __name__ == "__main__":
    functions = Functions()
    import boto3
    import io
    from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations

    BUCKET = "csv-file-store-ec51f700"
    LAW_KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html"

    # Instancier la classe
    functions = Functions()

    # Portefeuille initial
    functions.importPorteFolio({
        "AAPL": 5, "MSFT": 15, "GOOGL": 8, "AMZN": 12, "TSLA": 7,
        "META": 10, "NVDA": 9, "PEP": 11, "COST": 6, "AVGO": 13
    })

    # Récupérer le texte du fichier S3
    s3 = boto3.client("s3")
    law_content = s3.get_object(Bucket=BUCKET, Key=LAW_KEY)["Body"]
    SUM_LAW = getLawInformations(law_content)

    # Top 10 entreprises
    print("Top 10 entreprises:")
    print(functions.getTop10(SUM_LAW, "Court terme"))

    # Calcul des impacts positifs
    print("COMPUTING positive impact...")
    functions.computePositiveImpact(functions.portefolio, SUM_LAW)

    print("Portefeuille enrichi:", functions.portefolio)

    # 🔹 Mettre à jour le portefeuille avec debug
    print("\nUpdating portfolio with max delta 5%...")
    functions.updatePortefolio(max_delta=5.0)

    print("\nNouveau portefeuille:")
    for k, v in functions.new_portefolio.items():
        print(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")

    print(f"\nFinal Espace Disponible: {functions.espace_disponible:.2f}")

    # Dessiner comparaison
    print("\nDrawing portfolio comparison...")
    img = functions.plot_portfolio_comparison()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Upload vers S3
    KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/Camenbert/new_portefolio.png"
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=buffer.getvalue(), ContentType="image/png")
    buffer.close()

    functions.suggestStocks(5, BUCKET, "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings")
    print(f"✅ New portfolio image uploaded to s3://{BUCKET}/{KEY}")

functions = Functions()