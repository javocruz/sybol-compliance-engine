import re
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGULATIONS_DIR = PROJECT_ROOT / "research" / "regulations"

REGULATION_NAME_MAP = {
    "eu_ai_act": "EU AI Act",
    "gdpr": "GDPR",
    "codigo_penal": "Código Penal (LO 10/1995)",
    "lopdgdd": "LOPDGDD",
    "ley_13_2022": "Ley 13/2022 (Comunicación Audiovisual)",
}


def load_documents():
    reader = SimpleDirectoryReader(
        input_dir=str(REGULATIONS_DIR),
        required_exts=[".pdf"],
        file_metadata=lambda path: {
            "regulation_name": REGULATION_NAME_MAP.get(
                Path(path).stem, Path(path).stem
            ),
            "regulation_type": Path(path).stem,
            "source_path": path,
        },
    )
    return reader.load_data()


# Matches English "Article 50", Spanish "Artículo 50" / "Art. 50".
ARTICLE_RE = re.compile(r"\b(?:Articul[oa]|Art[íi]culo|Article|Art\.)\s*(\d+)", re.IGNORECASE)
SECTION_RE = re.compile(
    r"(?:Section|Chapter|Secci[óo]n|Cap[íi]tulo|T[íi]tulo)\s+(\d+[\w.]*)",
    re.IGNORECASE,
)


def chunk_documents(documents):
    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=64,
    )

    nodes = splitter.get_nodes_from_documents(documents)

    # Article/section headers usually appear once and govern the following
    # chunks, so carry the last-seen value forward (reset per source document)
    # instead of marking every header-less chunk "unknown".
    current_article = "unknown"
    current_section = "unknown"
    current_source = None

    for node in nodes:
        source = node.metadata.get("source_path") or node.metadata.get(
            "regulation_type"
        )
        if source != current_source:
            current_source = source
            current_article = "unknown"
            current_section = "unknown"

        text = node.get_content()

        article_matches = ARTICLE_RE.findall(text)
        if article_matches:
            node.metadata["article_number"] = article_matches[0]
            current_article = article_matches[-1]
        else:
            node.metadata["article_number"] = current_article

        section_matches = SECTION_RE.findall(text)
        if section_matches:
            node.metadata["section"] = section_matches[0]
            current_section = section_matches[-1]
        else:
            node.metadata["section"] = current_section

    return nodes
