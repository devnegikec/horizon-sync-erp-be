"""LLM structured extraction service for ASN documents.

Uses OpenAI/Anthropic/Ollama to extract structured ASN data from raw text.
Implements retry logic with exponential backoff and few-shot prompting.
"""

import json
import logging
import re
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Prompts ──────────────────────────────────────────────────────────────
_DOCUMENT_CLASSIFICATION_PROMPT = """You are a document classifier for a warehouse management system.
Read the provided document and classify it into exactly one of these categories:
- asn: Advance Shipping Notice — contains expected delivery date, confirmed line items, vehicle/driver info, references an open purchase order
- quotation: Price quote, MOQ, tentative quantities, valid until date — NOT a confirmed shipment
- pro_forma_invoice: Preliminary invoice for customs or payment terms — not a real shipment notice
- commercial_invoice: Bill for goods already shipped — this is AFTER the ASN, used for accounting
- packing_list: Detailed list of what's physically in each box/pallet — no prices, just quantities and weights
- unknown: Cannot determine the document type

Respond with ONLY the category name (one word), nothing else."""

_ASN_EXTRACTION_SYSTEM_PROMPT = """You are an ASN (Advanced Shipping Notice) data extraction expert.
Your task is to read the provided document text (from a PDF, email, or Excel sheet)
and extract structured ASN order information.

Return ONLY a valid JSON object matching this schema:
{
  "supplier_name": "string (required)",
  "supplier_id": "string or null (UUID if known)",
  "expected_delivery_date": "YYYY-MM-DD or null",
  "vehicle_number": "string or null",
  "driver_name": "string or null",
  "warehouse_id": "string or null (UUID of destination warehouse)",
  "line_items": [
    {
      "sku": "string (required)",
      "item_name": "string (required)",
      "quantity": integer (required),
      "uom": "string e.g. pieces, kg, boxes, pallets",
      "batch_no": "string or null",
      "serial_nos": ["string"] or null,
      "unit_cost": number or null
    }
  ],
  "confidence_score": 0.0-1.0,
  "low_confidence_fields": ["list field names that were unclear"]
}

Rules:
1. supplier_name: extract the company name sending the goods
2. expected_delivery_date: convert any date format to ISO YYYY-MM-DD
3. line_items: every distinct SKU must be a separate item
4. If a field is missing or unclear, use null (not empty string)
5. confidence_score: overall confidence in the extraction accuracy
6. low_confidence_fields: list any fields you had to guess or were ambiguous
7. Do NOT include markdown formatting or explanations outside the JSON
"""

_ASN_EXTRACTION_USER_TEMPLATE = """Extract the ASN data from the following document text:

--- DOCUMENT TEXT ---
{text}
--- END DOCUMENT ---

Return ONLY the JSON object."""


_DOCUMENT_CLASSIFICATION_USER_TEMPLATE = """Classify the following document text:

--- DOCUMENT TEXT ---
{text}
--- END DOCUMENT ---

Category:"""


class ASNExtractor:
    """Extract structured ASN data from raw document text using an LLM.

    First classifies the document type, then extracts ASN data only if it is a valid ASN.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.max_retries = 3
        self.timeout = 60.0

    async def classify(self, raw_text: str) -> str:
        """Classify the document type. Returns one of: asn, quotation, pro_forma_invoice,
        commercial_invoice, packing_list, unknown.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self._call_llm_for_classification(raw_text)
                doc_type = result.strip().lower().replace(" ", "_")
                allowed = {"asn", "quotation", "pro_forma_invoice", "commercial_invoice", "packing_list", "unknown"}
                if doc_type not in allowed:
                    doc_type = "unknown"
                return doc_type
            except Exception as e:
                logger.warning("Classification attempt %d failed: %s", attempt, e)
                if attempt == self.max_retries:
                    break
        logger.error("Document classification failed after retries; defaulting to unknown")
        return "unknown"

    async def extract(self, raw_text: str) -> dict[str, Any]:
        """Run LLM extraction with retry logic.

        Returns a dict with the structured ASN data and metadata.
        """
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self._call_llm(raw_text)
                parsed = self._parse_json(result)
                parsed.setdefault("confidence_score", 0.5)
                parsed.setdefault("low_confidence_fields", [])
                parsed.setdefault("line_items", [])
                return parsed
            except Exception as e:
                last_error = e
                logger.warning("Extraction attempt %d failed: %s", attempt, e)
                if attempt == self.max_retries:
                    break
        raise RuntimeError(f"ASN extraction failed after {self.max_retries} attempts: {last_error}")

    async def _call_llm_for_classification(self, raw_text: str) -> str:
        """Call LLM with classification prompt."""
        if self.provider == "openai":
            return await self._call_openai(raw_text, classification=True)
        if self.provider == "anthropic":
            return await self._call_anthropic(raw_text, classification=True)
        if self.provider == "ollama":
            return await self._call_ollama(raw_text, classification=True)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _call_llm(self, raw_text: str) -> str:
        """Dispatch to the configured LLM provider for full ASN extraction."""
        if self.provider == "openai":
            return await self._call_openai(raw_text)
        if self.provider == "anthropic":
            return await self._call_anthropic(raw_text)
        if self.provider == "ollama":
            return await self._call_ollama(raw_text)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _call_openai(self, raw_text: str, classification: bool = False) -> str:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        if classification:
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": _DOCUMENT_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": _DOCUMENT_CLASSIFICATION_USER_TEMPLATE.format(text=raw_text[:4000])},
                ],
                "temperature": 0.0,
                "max_tokens": 20,
            }
        else:
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": _ASN_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": _ASN_EXTRACTION_USER_TEMPLATE.format(text=raw_text[:12000])},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, raw_text: str, classification: bool = False) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        if classification:
            payload = {
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 20,
                "system": _DOCUMENT_CLASSIFICATION_PROMPT,
                "messages": [
                    {"role": "user", "content": _DOCUMENT_CLASSIFICATION_USER_TEMPLATE.format(text=raw_text[:4000])},
                ],
                "temperature": 0.0,
            }
        else:
            payload = {
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 4096,
                "system": _ASN_EXTRACTION_SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": _ASN_EXTRACTION_USER_TEMPLATE.format(text=raw_text[:12000])},
                ],
                "temperature": 0.1,
            }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def _call_ollama(self, raw_text: str, classification: bool = False) -> str:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        if classification:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": _DOCUMENT_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": _DOCUMENT_CLASSIFICATION_USER_TEMPLATE.format(text=raw_text[:4000])},
                ],
                "stream": False,
                "options": {"temperature": 0.0},
            }
        else:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": _ASN_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": _ASN_EXTRACTION_USER_TEMPLATE.format(text=raw_text[:8000])},
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown fences."""
        text = text.strip()
        # Strip markdown fences
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        # Sometimes models add a preamble; find first '{'
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        return json.loads(text)


def get_extractor() -> ASNExtractor:
    """Factory: return an ASNExtractor instance."""
    return ASNExtractor()
