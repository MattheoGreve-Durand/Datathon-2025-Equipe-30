import boto3
import instructor
import os
from IPython.display import Markdown, display
from pydantic import BaseModel
from bs4 import BeautifulSoup
import re

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)


class Company10k(BaseModel):
    business_resume: str
    business_model: str
    risk_factor: list[str]
    property: list[str]
    sector: list[str]
    sub_sector: list[str]
    country_headquarters: list[str]
    country_of_production: list[str]
    country_of_operation: list[str]
    country_of_ressource: list[str]
    client_country: list[str]
    client_type: list[str]


BUCKET = "csv-file-store-ec51f700"
BASE_PREFIX = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings/"
OUTPUT_PREFIX = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillingsResume"


def extract_relevant_sections(html_text):
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "table"]):
        tag.extract()

    text = soup.get_text(separator="\n")

    text = re.sub(r'\s+', ' ', text)  # supprimer les espaces multiples
    text = text.replace("\xa0", " ")  # supprimer les caractères spéciaux
    text_upper = text.upper()

    def extract_section(start_marker, end_marker):
        start = text_upper.find(start_marker)
        if start == -1:
            return ""
        end = text_upper.find(end_marker, start)
        if end == -1:
            end = len(text_upper)
        return text[start:end]

    sections = [
        extract_section("ITEM 1.", "ITEM 1A."),  # Business
        extract_section("ITEM 1A.", "ITEM 2."),  # Risk Factors
        extract_section("ITEM 2.", "ITEM 3."),   # Properties
        extract_section("ITEM 7.", "ITEM 7A."),  # MD&A
    ]

    combined_text = "\n\n".join([s for s in sections if s.strip() != ""])
    return combined_text.strip()


def get10kInformations(bucket: str, key: str) -> Company10k:
    obj = s3.get_object(Bucket=bucket, Key=key)
    text_10K = obj["Body"].read().decode("utf-8")

    text_to_analyze = extract_relevant_sections(text_10K)

    response = client.chat.completions.create(
        modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are an expert financial and regulatory analyst specialized in SEC filings (10-K reports).\n\n"
                    "Extract the following information from the company report below, following this exact schema:\n\n"
                    "1. **business_resume** – A detailed summary (2 entences) of what the company does, its main activities, and markets.\n"
                    "2. **business_model** – A clear explanation (2 sentences) of how the company makes money (main sources of revenue or services provided).\n"
                    "3. **risk_factor** – A list of key risks (3 sentences) (business, regulatory, financial, environmental, or geopolitical) mentioned in the report.\n"
                    "4. **property** – List of important physical assets (factories, offices, warehouses, data centers, etc.).\n"
                    "5. **sector** – Main industry sectors in which the company operates (e.g., Technology, Energy, Finance, Healthcare, etc.).\n"
                    "6. **sub_sector** – More specific activity segments (e.g., Semiconductor Manufacturing, Cloud Services, Retail Banking, etc.).\n"
                    "7. **country_headquarters** – Country or countries where the company’s headquarters are located.\n"
                    "8. **country_of_production** – Countries where the main manufacturing or production takes place.\n"
                    "9. **country_of_operation** – Countries where the company operates, sells products, or provides services.\n"
                    "10. **country_of_ressource** – Countries where the company extracts or sources key raw materials or resources.\n"
                    "11. **client_country** – Main countries or regions where the company’s clients or customers are located.\n"
                    "12. **client_type** – Types of clients the company serves (choose from: 'private companies', 'public companies', 'governments', 'individual consumers').\n\n"
                    f"{text_to_analyze}"
                ),
            },
        ],
        response_model=Company10k,
        inferenceConfig={
            "maxTokens": 64000,
        }
    )
    return response


def process_all_fillings():
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET, Prefix=BASE_PREFIX)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".html"):
                continue

            print(f"🔍 Processing: {key}")

            try:
                company_data = get10kInformations(BUCKET, key)
                json_data = company_data.model_dump_json(indent=2)

                output_key = key.replace("/fillings/", "/fillingsResume/").replace(".html", ".json")

                s3.put_object(
                    Bucket=BUCKET,
                    Key=output_key,
                    Body=json_data.encode("utf-8"),
                    ContentType="application/json",
                )
                print(f"✅ Saved: {output_key}")

            except Exception as e:
                print(f"❌ Error processing {key}: {e}")


if __name__ == "__main__":
    process_all_fillings()