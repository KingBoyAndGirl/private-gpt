# mypy: ignore-errors

"""Read RDF files.

This module is used to read RDF files.
It was created by llama-hub but it has not been ported
to llama-index==0.1.0 with multiples changes to fix the code.

Original code:
https://github.com/run-llama/llama-hub
"""

import logging
from pathlib import Path
from typing import Any, List, Dict, Optional, Union

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

logger = logging.getLogger(__name__)


class RDFReader(BaseReader):
    """RDF reader."""

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize loader."""
        super().__init__(*args, **kwargs)

    def fetch_labels(self, uri: URIRef, graph: Graph, lang: str) -> List[str]:
        """Fetch all labels of a URI by language."""
        return [
            label.value
            for label in graph.objects(uri, RDFS.label)
            if label.language in [lang, None]
        ]

    def fetch_label_in_graphs(self, uri: URIRef, lang: str = "en") -> str:
        """Fetch one label of a URI by language from the local or global graph."""
        labels = self.fetch_labels(uri, self.g_local, lang)
        if labels:
            return labels[0]

        labels = self.fetch_labels(uri, self.g_global, lang)
        if labels:
            return labels[0]

        return str(uri)

    def load_data(self, file: Path, extra_info: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Parse file."""
        extra_info = extra_info or {}
        extra_info["graph_type"] = "rdf"
        lang = extra_info.get("lang", "en")

        self.g_local = Graph()
        try:
            self.g_local.parse(file)
        except Exception as e:
            logger.error(f"Failed to parse local RDF file {file}: {e}")
            return []

        self.g_global = Graph()
        try:
            self.g_global.parse(str(RDF))
            self.g_global.parse(str(RDFS))
        except Exception as e:
            logger.error(f"Failed to parse RDF/RDFS graph: {e}")
            return []

        text_list = []

        for s, p, o in self.g_local:
            logger.debug("s=%s, p=%s, o=%s", s, p, o)
            if p == RDFS.label:
                continue

            subj_label = self.fetch_label_in_graphs(s, lang=lang)
            pred_label = self.fetch_label_in_graphs(p, lang=lang)
            obj_label = self.fetch_label_in_graphs(o, lang=lang)

            if not subj_label or not pred_label or not obj_label:
                continue

            triple = f"<{subj_label}> <{pred_label}> <{obj_label}>"
            text_list.append(triple)

        text = "\n".join(text_list)
        return [self._text_to_document(text, extra_info)]

    def _text_to_document(self, text: str, extra_info: Optional[Dict[str, Any]] = None) -> Document:
        return Document(text=text, extra_info=extra_info or {})

