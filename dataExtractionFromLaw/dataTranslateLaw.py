import boto3
import html
from bs4 import BeautifulSoup

def translate_html_file(html_content, source_lang="auto", target_lang="en", output_path=None):
    """
    Traduit un fichier HTML à l'aide d'Amazon Translate (boto3).

    Args:
        file_path (str): chemin vers le fichier HTML source.
        source_lang (str): code langue source (ex: 'en', 'de', 'es').
        target_lang (str): code langue cible (ex: 'fr', 'en', 'es').
        output_path (str, optional): si spécifié, sauvegarde le HTML traduit dans ce fichier.

    Returns:
        str: le contenu HTML traduit.
    """

    # === 1. Initialiser le client Amazon Translate ===
    translate = boto3.client("translate")

    # === 3. Extraire le texte tout en conservant la structure HTML ===
    # BeautifulSoup permet d’identifier les zones textuelles à traduire
    soup = BeautifulSoup(html_content, "html.parser")

    # === 4. Traduire uniquement les noeuds textuels ===
    for element in soup.find_all(string=True):
        text = element.strip()
        if text:
            try:
                response = translate.translate_text(
                    Text=text,
                    SourceLanguageCode=source_lang,
                    TargetLanguageCode=target_lang,
                    Settings={"Formality": "FORMAL"},
                    TerminologyNames=[]
                )
                translated_text = html.unescape(response["TranslatedText"])
                element.replace_with(translated_text)
            except Exception as e:
                print(f"⚠️ Erreur de traduction sur le texte : '{text[:40]}...' → {e}")

    # === 5. Obtenir le HTML traduit final ===
    translated_html = str(soup)

    # === 6. Optionnel : sauvegarde dans un nouveau fichier ===
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_html)
        print(f"✅ Fichier traduit sauvegardé dans : {output_path}")

    return translated_html

def detect_language(text: str) -> str:
    """
    Detects the dominant language in a large text by analyzing only half of it.
    (Amazon Comprehend has a 5 000-byte limit per request.)
    """
    comprehend = boto3.client("comprehend")
    if not text:
        return "auto"

    # Use half of the text to reduce payload size
    half_index = len(text) // 2
    sample_text = text[:half_index]

    # Ensure we don’t exceed Comprehend’s max text size
    sample_text = sample_text[:4900]

    try:
        response = comprehend.detect_dominant_language(Text=sample_text)
        languages = response.get("Languages", [])
        if not languages:
            return "auto"

        dominant_lang = max(languages, key=lambda l: l["Score"])["LanguageCode"]
        print(f"🌍 Detected language: {dominant_lang}")
        return dominant_lang
    except Exception as e:
        print(f"⚠️ Error detecting language: {e}")
        return "auto"




if __name__ == "__main__":
    BUCKET_NAME = "csv-file-store-ec51f700"
    KEY = "dzd-3lz7fcr1rwmmkw/5h6d6xccl72dn4/dev/data/directives/5.中华人民共和国能源法__中国政府网.html"
    s3 = boto3.client("s3")
    file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    file_content = file_obj["Body"].read().decode("utf-8")
    print(translate_html_file(file_content))

    