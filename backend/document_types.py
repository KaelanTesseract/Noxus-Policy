# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""What a document is, and what it may change.

The kind of letter (see ``document_naming.detect_kind``) decides the document type
shown in the upload dialog. Letters that only inform - terms and conditions,
consumer information, the green card - are filed away and never touch the
contract data: their text is full of amounts, dates and classes that belong to no
particular policy ("3,00 € Mahngebühr", "Regionalklasse 1 bis 12", ...).

The values are the entries of the document-type list in the frontend
(``UploadModal.tsx``) - keep both in sync.
"""

from typing import Optional

DEFAULT_DOC_TYPE = "Versicherungsschein / Polizze"

# kind of letter -> entry of the document-type list
DOC_TYPE_FOR_KIND = {
    "Versicherungsschein": "Versicherungsschein / Polizze",
    "Beitragsrechnung": "Beitragsrechnung",
    "Beitragsanpassung": "Beitragsanpassung",
    "Nachtrag": "Nachtrag / Änderungsschein",
    "Nachtrag zum Vertragsende": "Nachtrag / Änderungsschein",
    "Verbraucherinformationen": "Verbraucherinformationen",
    "Produktinformationsblatt": "Kundeninformationen",
    "Produktinformationsblatt und Bedingungen": "Kundeninformationen",
    "Allgemeine Bedingungen": "Kundeninformationen",
    "Grüne Karte": "Sonstiges",
    "Schadenvisitenkarten": "Sonstiges",
}

# Same rule as isInformationalDocType() in UploadModal.tsx.
_INFORMATIONAL_WORDS = (
    "sonstig", "verbraucherinformation", "kundeninformation",
    "informationsblatt", "produktinformation", "beratungsprotokoll",
)

# Fields that describe the contract. An informational document must not deliver any of them.
CONTRACT_FIELDS = (
    "cost", "new_cost", "previous_cost", "start_date", "end_date", "cancellation_date",
    "sf_class", "regional_class", "type_class", "payment_cycle",
)


def is_informational(doc_type: Optional[str]) -> bool:
    """True for documents that are archived only and must not update an insurance."""
    lowered = (doc_type or "").lower().strip()
    return any(word in lowered for word in _INFORMATIONAL_WORDS)


def document_type_for(kind: Optional[str]) -> Optional[str]:
    return DOC_TYPE_FOR_KIND.get(kind) if kind else None
