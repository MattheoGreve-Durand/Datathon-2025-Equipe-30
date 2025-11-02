import boto3
import instructor
import json
import path
import sys
import os
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dataExtractionFromLaw.dataExtractionFromLaw import getLawInformations

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

BUCKET_NAME = "csv-file-store-ec51f700"
PREFIX = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillingsResume"

response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)
print(response)


class Score(BaseModel):
    score: int
    reasoning: str


def getScoreAndReasoning(data: str, law: str) -> Score:
    response = client.chat.completions.create(
            modelId="global.anthropic.claude-sonnet-3-20251001-v1:0",
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
                        "  \"reasoning\": <textual explanation of your reasoning>\n"
                        "}\n\n"
                        "Here are the inputs:\n\n"
                        f"--- COMPANY DATA ---\n{data}\n\n"
                        f"--- LAW DATA ---\n{law}"
                    ),
                },
            ],
            response_model=Score,
            inferenceConfig={
                "maxTokens": 64000,
            }
        )

    return {"score": response.score, "reasoning": response.reasoning}


def getConcernedEntreprises(law_summarized: str, entreprises_path: str) -> dict:

    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)

    if "Contents" not in response:
        print("Aucun fichier trouvé dans ce chemin S3.")
    else:
        results = {}
        for obj in response["Contents"]:
            key = obj["Key"]
            folder_name = path.dirname(key).split('/')[-1]

            if not key.endswith(".json"):
                continue

            print(f"📂 Lecture du fichier : {key}")

            continue

            file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            file_content = file_obj["Body"].read().decode("utf-8")


            try:
                data = json.loads(file_content)
                results[folder_name] = getScoreAndReasoning(data, law_summarized)

            except json.JSONDecodeError:
                print(f"⚠️ Erreur de parsing JSON dans {key}")
                continue
        return results


if __name__ == "__main__":
    law_sum = getLawInformations("csv-file-store-ec51f700", "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html")
    getConcernedEntreprises(law_sum, PREFIX)
