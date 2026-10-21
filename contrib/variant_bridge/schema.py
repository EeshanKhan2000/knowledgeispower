"""JSON schemas for ``variant_to_complexes`` (S1). Changing these requires Amit's approval."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Gene symbol (current, alias or previous HGNC symbol), Ensembl gene ID "
            "(ENSG...), or HGVS-style variant, e.g. 'PSMB5:c.100A>G', "
            "'NM_002797.5(PSMB5):c.100A>G', 'ENST00000361611:c.100A>G'.",
        },
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": ["corum", "complexportal"]},
            "default": ["corum", "complexportal"],
        },
        "dataset_proteins": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional dataset feature ids (UniProt accessions or 'P1;P2' protein "
            "groups). Each partner gets in_dataset=true if any group contains it.",
        },
    },
    "required": ["query"],
}

_PARTNER = {
    "type": "object",
    "properties": {
        "uniprot": {"type": "string"},
        "symbols": {"type": "array", "items": {"type": "string"}},
        "in_dataset": {"type": ["boolean", "null"]},
    },
    "required": ["uniprot", "symbols", "in_dataset"],
}

_COMPLEX = {
    "type": "object",
    "properties": {
        "complex_id": {"type": "string"},
        "source": {"type": "string", "enum": ["corum", "complexportal"]},
        "name": {"type": "string"},
        "members": {"type": "array", "items": {"type": "string"}},
        "partners": {"type": "array", "items": _PARTNER},
    },
    "required": ["complex_id", "source", "name", "members", "partners"],
}

OUTPUT_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "input_type": {"type": "string", "enum": ["gene_symbol", "ensembl_gene", "hgvs"]},
                "resolved_gene": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "how": {"type": "string", "enum": ["symbol", "prev", "alias", "ensembl", "hgvs_gene", "hgvs_transcript"]},
                    },
                    "required": ["symbol", "how"],
                },
                "uniprot": {"type": "array", "items": {"type": "string"}},
                "complexes": {"type": "array", "items": _COMPLEX},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query", "input_type", "resolved_gene", "uniprot", "complexes", "warnings"],
        },
        {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "enum": ["invalid_input", "unresolved_input", "ambiguous_symbol", "unsupported_variant", "upstream_unavailable"]},
                        "message": {"type": "string"},
                        "query": {"type": ["string", "null"]},
                        "candidates": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["code", "message", "query"],
                }
            },
            "required": ["error"],
        },
    ]
}
