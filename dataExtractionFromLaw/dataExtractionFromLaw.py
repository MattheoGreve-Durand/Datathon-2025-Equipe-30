import boto3
import instructor
import BaseModel

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


BUCKET = "csv-file-store-ec51f700"
KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/1.DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html"


def getLawInformations(bucket: str = BUCKET, key: str = KEY) -> Law:
    obj = s3.get_object(Bucket=bucket, Key=key)
    text_of_law = obj["Body"].read().decode("utf-8")
    response = client.chat.completions.create(
        modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the following information from the text below, according to the schema:\n\n"
                    "1. **countrys** – list of countries where the regulation applies, direct list of the countries affected, no approximation.\n"
                    "2. **sectors_of_activity** – list of industries or business sectors mentioned\n"
                    "3. **regulation_types** – type(s) of regulation (environmental, financial, privacy...)\n"
                    "4. **date_of_application** – when the law or measure starts to apply\n"
                    "5. **measures_imposed** – the specific actions, limits or obligations imposed, try to use numbers and details as much as possible\n\n"
                    "13. **severity** – A number from 0 to 5 indicating how severe or strict the main regulations or compliance risks mentioned are.\n\n"
                    "   - 0 = No regulatory constraints.\n"
                    "   - 1 = Very mild or generic compliance.\n"
                    "   - 2 = Lightly constrained by regulation.\n"
                    "   - 3 = Moderate risk from regulations.\n"
                    "   - 4 = Strong regulatory oversight or exposure.\n"
                    "   - 5 = Extremely strict regulation or high legal exposure.\n\n"
                
                    "Text to analyze:\n\n"
                    f"{text_of_law}"
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
    law_info = getLawInformations()
    print(law_info)