from bs4 import BeautifulSoup
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
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if cells:
                rows_text.append("\t".join(cells))
        if rows_text:
            extracted_tables.append("[TABLE]\n" + "\n".join(rows_text) + "\n[/TABLE]")

    return "\n\n".join(extracted_tables).strip()
