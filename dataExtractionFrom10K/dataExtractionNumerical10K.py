from bs4 import BeautifulSoup
import re
import boto3
import instructor


def extract_only_tables(html_text: str) -> str:
    """
    Extrait uniquement le contenu des balises <table> d’un document HTML (10-K),
    et renvoie le tout en texte lisible.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    tables = soup.find_all("table")
    extracted_tables = []

    for table in tables:
        rows_text = []
        for row in table.find_all("tr"):
            # Récupérer chaque cellule (th ou td)
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if cells:
                rows_text.append("\t".join(cells))
        if rows_text:
            extracted_tables.append("[TABLE]\n" + "\n".join(rows_text) + "\n[/TABLE]")

    return "\n\n".join(extracted_tables).strip()

s3 = boto3.client("s3")
bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

BUCKET = "csv-file-store-ec51f700"
BASE_PREFIX = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/fillings/AAPL/2024-11-01-10k-AAPL.html"

obj = s3.get_object(Bucket=BUCKET, Key=BASE_PREFIX)
text_10K = obj["Body"].read().decode("utf-8")

numerical_10K = extract_only_tables(text_10K)
print(numerical_10K)