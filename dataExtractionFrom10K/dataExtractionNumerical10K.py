import boto3
import instructor
from pydantic import BaseModel
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from tableExtractionFrom10K import extract_only_tables

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

BUCKET = "csv-file-store-ec51f700"
KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings/AAPL/2024-11-01-10k-AAPL.html"

class Numerical_10K(BaseModel):
    net_income: int
    revenue: int
    preferred_dividend: float
    average_of_CS: int
    she: int
    total_asset:int
    eps_current: float
    eps_previous: float
    revenue_current: int
    revenue_previous: int
    asset_current: int
    liabilities_current: int
    total_debt: int
    operating_income: int
    cost_of_good_sold: int
    inventory_avg: int
    cost_of_debt: int
    corporate_tax_rate: float



def getNumericalFrom10K(text_of_tables: str) -> Numerical_10K:
    response = client.chat.completions.create(
        modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a professional financial analyst specialized in SEC filings (10-K and 10-Q reports).\n"
                    "You are given **tables** extracted from a company's 10-K filing.\n"
                    "These tables contain numerical data such as revenues, income, assets, and liabilities.\n\n"
                    "Your task is to **extract** all the key financial metrics below according to the schema.\n"
                    "If a value cannot be found or inferred confidently, return `0`.\n"
                    "All numbers must be expressed as **integers**, without symbols, text, or currency units.\n"
                    "If multiple years are present, use the **most recent year**.\n\n"
                    
                    "If you do not find the data in the prompt, just return None for the value.\n"
                    "Not go on the internet"
                    "Do not make up any data.\n\n"

                    "Extract the following fields:\n\n"
                    "1. **net_income** – Net income (net earnings attributable to shareholders).\n"
                    "2. **revenue** – Total revenue (also called net sales or total operating revenues).\n"
                    "3. **preferred_dividend** – Preferred dividends paid during the year (if applicable, else 0). return a float for this value\n"
                    "4. **average_of_CS** – Average number of common shares outstanding.\n"
                    "5. **she** – Shareholders' equity (total equity or total stockholders’ equity).\n"
                    "6. **total_asset** – Total assets at the end of the period.\n"
                    "7. **eps_current** – Earnings per share (basic or diluted) for the current year. return a float for this value\n"
                    "8. **eps_previous** – Earnings per share (previous year, if available) return a float for this value\n"
                    "9. **revenue_current** – Total revenue for the current year.\n"
                    "10. **revenue_previous** – Total revenue for the previous year.\n"
                    "11. **asset_current** – Current assets (total current assets section).\n"
                    "12. **liabilities_current** – Current liabilities (total current liabilities section).\n"
                    "13. **total_debt** – Total debt (sum of long-term and short-term borrowings).\n"
                    "14. **operating_income** – Operating income (operating profit or EBIT).\n"
                    "15. **cost_of_good_sold** – Cost of goods sold (COGS or cost of revenue).\n"
                    "16. **inventory_avg** – Average inventory (use average between current and previous year if available, else 0).\n\n"
                    "17. **cost_of_debt** - cost of the debt from the last year"
                    "18. **corporate_tax_rate** - from the last year"

                    "Rules:\n"
                    "- If the value is shown in millions or thousands, convert it to full integer form (e.g., '1,234 million' → 1234000000).\n"
                    "- If both consolidated and parent-only data are shown, choose the **consolidated** figures.\n"
                    "- Prefer USD values if multiple currencies are listed.\n\n"

                    "Here are the financial tables extracted from the company's 10-K:\n\n"
                    f"{text_of_tables}"
                ),
            },
        ],
        response_model=Numerical_10K,
        inferenceConfig={
            "maxTokens": 64000,
        }
    )
    return response

if __name__ == "__main__":
    obj = s3.get_object(Bucket=BUCKET, Key=KEY)
    text_of_10K = obj["Body"].read().decode("utf-8")
    data = extract_only_tables(text_of_10K)
    print("============================================================================================")
    print(getNumericalFrom10K(data))