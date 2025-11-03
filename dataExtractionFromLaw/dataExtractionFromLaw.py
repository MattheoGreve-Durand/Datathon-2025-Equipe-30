import boto3
import instructor
from pydantic import BaseModel

from dataExtractionFromLaw.dataTranslateLaw import detect_language, translate_html_file

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)


class Law(BaseModel):
    countrys: list[str]
    sectors_of_activity: list[str]
    regulation_types: list[str]
    date_of_application: list[str]
    measures_imposed: list[str]
    severity: int
    time_before_application: int
    time_of_application: int
    revision_probability: float


def getLawInformations(file) -> Law:
    text_of_law = file.read().decode("utf-8")

    #detected_lang = detect_language(text_of_law)

    #if detected_lang != "en":
        #text_of_law = translate_html_file(text_of_law)

    response = client.chat.completions.create(
        modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[
            {
                "role": "user",
                "content": ( f"""
                    Extract the following information from the text below, according to the schema:

                    1. **countrys** – list of countries where the regulation applies, direct list of the countries affected, no approximation.

                    2. **sectors_of_activity** – list of industries or business sectors mentioned

                    3. **regulation_types** – type(s) of regulation (environmental, financial, privacy...)

                    4. **date_of_application** – when the law or measure starts to apply

                    5. **measures_imposed** – the specific actions, limits or obligations imposed, try to use numbers and details as much as possible

                    13. **severity** – A number from 0 to 5 indicating how severe or strict the main regulations or compliance risks mentioned are.
                    - 0 = No regulatory constraints.
                    - 1 = Very mild or generic compliance.
                    - 2 = Lightly constrained by regulation.
                    - 3 = Moderate risk from regulations.
                    - 4 = Strong regulatory oversight or exposure.
                    - 5 = Extremely strict regulation or high legal exposure.

                    14. **time_before_application** – Time in month before the measures are in effect. (return an Integer)

                    15. **time_of_application** – Time in month of how long the regulations or compliance measures are in effect. (return an Integer)

                    16. **revision_probability** – A decimal number from 0 to 1 indicating the likelihood that this law will be revised or modified in the future. Apply these rules:
                    - If the law explicitly mentions a revision schedule → calculate value based on timeframe (e.g., 1 year → 1.0, 3 years → 0.8, 5 years → 0.6)
                    - If no revision is mentioned but the regulation type is known to evolve frequently (fiscal, environmental, digital) → assign 0.6-0.8
                    - If it's a structural or foundational law (constitutional, criminal code, civil code, etc.) → assign 0.2-0.4
                    - Default value if uncertain → 0.5

                    Text to analyze:

                    {text_of_law}"""
                ),
            },
        ],
        response_model=Law,
        inferenceConfig={
            "maxTokens": 64000,
        }
    )
    return response


if __name__ == "__main__":
    BUCKET = "csv-file-store-ec51f700"
    KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html"
    file = s3.get_object(Bucket=BUCKET, Key=KEY)
    law_info = getLawInformations(file["Body"])
    print(law_info)