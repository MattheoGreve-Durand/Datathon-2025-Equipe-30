import boto3
import instructor
import json
import sys
import os
import math
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

BUCKET_NAME = "csv-file-store-ec51f700"
PREFIX = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillingsResume"


class Score(BaseModel):
    score: int
    reasoning: str


def getScoreAndReasoning(data: str, law: str) -> Score:
    response = client.chat.completions.create(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are an expert in corporate regulatory analysis.\n"
                        "Your task is to assess how much a **new law or directive** impacts a given company.\n\n"
                        "You will receive two JSON documents:\n"
                        "1. The **company's 10-K summary**, describing its business model, sectors, countries of operation, and risk factors.\n"
                        "2. The **law summary**, describing the countries, sectors, regulation types, measures imposed, and date of application.\n\n"
                        "Your goal is to produce two outputs:\n"
                        "- **score** (integer 0–5): a numeric estimate of how strongly the law impacts this company.\n"
                        "- **reasoning** (string): a detailed justification for that score, citing specific matches or mismatches between the law and the company.\n\n"
                        "Scoring scale:\n"
                        "0 → No impact (law unrelated to company's sector or geography)\n"
                        "1 → Minimal impact (indirect or partial exposure)\n"
                        "2 → Limited impact (only some operations or markets affected)\n"
                        "3 → Moderate impact (noticeable operational or compliance costs)\n"
                        "4 → High impact (affects core business or significant regulatory burden)\n"
                        "5 → Very high impact (fundamental change, major compliance costs, or legal risk)\n\n"
                        "Consider:\n"
                        "- Whether the company operates in countries where the law applies.\n"
                        "- Whether its sectors or sub-sectors are mentioned in the law.\n"
                        "- Whether its risk factors already reference similar regulations.\n"
                        "- Whether the imposed measures directly restrict or burden its activities.\n"
                        "- Whether the law’s effective date aligns with the company’s current operations.\n\n"
                        "Return your analysis following this schema:\n"
                        "{\n"
                        "  \"score\": <integer between 0 and 5>,\n"
                        "  \"reasoning\": <textual explanation of your reasoning (1 sentence)>\n"
                        "}\n\n"
                        "Here are the inputs:\n\n"
                        f"--- COMPANY DATA ---\n{data}\n\n"
                        f"--- LAW DATA ---\n{law}"
                    ),
                },
            ],
            response_model=Score,
            inferenceConfig={
                "maxTokens": 4096,
            }
        )

    return {"score": response.score, "reasoning": response.reasoning}


def getConcernedEntreprises(law_summarized, entreprises_path: str, investment_horizon, max_workers: int = 7) -> dict:
    Alpha = 1 #court terme
    Beta = 0.8
    Gama = 0.06
    t_eff = 6 - law_summarized.time_before_application
    if (investment_horizon == "Moyen terme"):
        Beta = 0.535
        Gama = 0.06
        t_eff = 24 - law_summarized.time_before_application
    elif (investment_horizon == "Long terme"):
        Beta = 0.4
        Gama = 0.1
        t_eff = 60 - law_summarized.time_before_application

    if (t_eff < 0): t_eff = 0

    def temporal_impact(Alpha, Beta, Gama, t_eff, t_conformite, revision_probability):
        try:
            return Alpha * math.exp(
                -Beta * ((t_eff) / (t_conformite))
            ) + Gama * revision_probability
        except ZeroDivisionError:
            return 0
    
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)

    if "Contents" not in response:
        print("Aucun fichier trouvé dans ce chemin S3.")
        return {}

    results = {}

    def process_company(key):
        """Fonction exécutée dans chaque thread"""
        folder_name = os.path.dirname(key).split('/')[-1]
        try:
            file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            file_content = file_obj["Body"].read().decode("utf-8")
            data = json.loads(file_content)

            # ⚠️ Assure-toi que data contient t_conformite
            try:
                t_conformite = data.get("t_conformite", 1)
            except Exception as e:
                t_conformite = 1
                print(e)

            # Calcul du score via Bedrock
            result = getScoreAndReasoning(json.dumps(data), law_summarized.model_dump_json())

            # Score final pondéré
            score = result["score"]
            temporial = temporal_impact(Alpha, Beta, Gama, t_eff, t_conformite, law_summarized.revision_probability)
            score_final = score * temporial

            return folder_name, {
                "score": score,
                "impact_temporiel": temporial,
                "score_final": score_final,
            }

        except Exception as e:
            print(f"❌ Erreur sur {folder_name}: {e}")
            return folder_name, {"error": str(e)}

    # --- Thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_company, obj["Key"])
            for obj in response["Contents"]
            if obj["Key"].endswith(".json")
        ]

        for future in as_completed(futures):
            folder_name, result = future.result()
            results[folder_name] = result

    # Tri des résultats par score_final décroissant
    sorted_results = sorted(
            results.items(),
            key=lambda item: item[1].get("score_final", 0),
            reverse=True,
        )
    

    return dict(sorted_results[:100]), dict(sorted_results)
    #  change to a 100          ^

if __name__ == "__main__":
    law_sum = getLawInformations("csv-file-store-ec51f700", "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html")
    print("DEBUG: TOP10")