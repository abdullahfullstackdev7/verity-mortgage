from __future__ import annotations

from backend.app.db.models.enums import DocumentType
from backend.app.services.extraction.llm_fallback import extract_missing_fields_via_llm


class TestExtractMissingFieldsViaLlm:
    def test_no_provider_configured_returns_empty(self):
        result = extract_missing_fields_via_llm(
            DocumentType.PAYSTUB,
            "some ocr text",
            {"employer_name"},
            complete_fn=lambda prompt: None,
        )
        assert result == {}

    def test_empty_missing_fields_short_circuits_without_calling_provider(self):
        calls = []

        def fake_complete(prompt: str):
            calls.append(prompt)
            return ('{"employer_name": "Acme"}', "fake")

        result = extract_missing_fields_via_llm(DocumentType.PAYSTUB, "text", set(), complete_fn=fake_complete)
        assert result == {}
        assert calls == []

    def test_valid_response_resolves_only_requested_fields(self):
        def fake_complete(prompt: str):
            return (
                '{"employer_name": "Acme Corp", "gross_pay_current": 3846.25, "pay_frequency": "Biweekly"}',
                "fake-provider",
            )

        result = extract_missing_fields_via_llm(
            DocumentType.PAYSTUB,
            "ocr text",
            {"employer_name"},
            complete_fn=fake_complete,
        )
        assert set(result.keys()) == {"employer_name"}
        assert result["employer_name"].value == "Acme Corp"
        assert result["employer_name"].raw_text == "llm:fake-provider"
        assert 0 < result["employer_name"].confidence <= 1

    def test_null_field_in_response_is_not_resolved(self):
        def fake_complete(prompt: str):
            return ('{"employer_name": null}', "fake")

        result = extract_missing_fields_via_llm(
            DocumentType.PAYSTUB, "text", {"employer_name"}, complete_fn=fake_complete
        )
        assert result == {}

    def test_invalid_json_is_rejected(self):
        def fake_complete(prompt: str):
            return ("this is not json", "fake")

        result = extract_missing_fields_via_llm(
            DocumentType.PAYSTUB, "text", {"employer_name"}, complete_fn=fake_complete
        )
        assert result == {}

    def test_schema_validation_failure_is_rejected(self):
        def fake_complete(prompt: str):
            # gross_pay_current must be a number; this fails validation.
            return ('{"gross_pay_current": "not-a-number"}', "fake")

        result = extract_missing_fields_via_llm(
            DocumentType.PAYSTUB, "text", {"gross_pay_current"}, complete_fn=fake_complete
        )
        assert result == {}

    def test_unmapped_document_type_returns_empty(self):
        result = extract_missing_fields_via_llm(
            DocumentType.ID, "text", {"anything"}, complete_fn=lambda prompt: (None, None)
        )
        assert result == {}
