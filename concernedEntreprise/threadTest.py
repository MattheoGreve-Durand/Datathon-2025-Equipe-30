import boto3
import instructor
import json
import sys
import os
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


def getConcernedEntreprises(law_summarized: str, entreprises_path: str, max_workers: int = 7) -> dict:
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)

    if "Contents" not in response:
        print("Aucun fichier trouvé dans ce chemin S3.")
        return {}

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        for obj in response["Contents"]:
            key = obj["Key"]
            folder_name = os.path.dirname(key).split('/')[-1]

            if not key.endswith(".json"):
                continue

            file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            file_content = file_obj["Body"].read().decode("utf-8")

            try:
                data = json.loads(file_content)
                futures[executor.submit(getScoreAndReasoning, data, law_summarized)] = folder_name

            except json.JSONDecodeError:
                print(f"⚠️ Erreur de parsing JSON dans {key}")
                continue

        for future in as_completed(futures):
            folder_name = futures[future]
            try:
                result = future.result()
                results[folder_name] = result
                print(f"✅ {folder_name}: score={result['score']}")
            except Exception as e:
                print(f"❌ Erreur sur {folder_name}: {e}")

    sorted_results = dict(
        sorted(
            results.items(),
            key=lambda item: item[1]["score"] if "score" in item[1] else 0,
            reverse=True
        )
    )

    return sorted_results


if __name__ == "__main__":
    law_sum = getLawInformations("csv-file-store-ec51f700", "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html")
    getConcernedEntreprises(law_sum, PREFIX)
    