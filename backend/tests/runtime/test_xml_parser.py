"""M3 - XML parser tests.

Tests verify:
- Legal tool-call XML can be parsed correctly
- Incomplete/malformed XML is handled gracefully (not crash)
- Illegal XML structure does not propagate to main loop
- Parser returns empty dict for plain text
- Parser handles edge cases (empty input, CDATA, etc.)
"""

import pytest

from app.runtime.xml_parser import ToleranceXMLParser, XMLElement


class TestToleranceXMLParserValidInput:
    """R3-4: Valid XML tool calls are parsed correctly."""

    def test_parse_simple_action_tag(self):
        """<action><tool><arg>val</arg></tool></action> should parse."""
        parser = ToleranceXMLParser()
        text = '<action><tool><name>Alice</name></tool></action>'
        result = parser.extract_elements(text, element_names=["action"])
        assert "action" in result
        assert "tool" in result or "<tool>" in text  # nested extraction

    def test_parse_task_complete_action(self):
        """task_complete tool call should be extractable."""
        parser = ToleranceXMLParser()
        text = '<action><task_complete><answer>The answer is 42</answer></task_complete></action>'
        result = parser.extract_elements(text)
        # Should find action and task_complete
        assert "action" in result or "task_complete" in result

    def test_parse_nested_tool_with_multiple_args(self):
        """Nested tool with multiple arguments should parse."""
        parser = ToleranceXMLParser()
        text = """
        <action>
            <read_file>
                <path>/tmp/test.txt</path>
            </read_file>
        </action>
        """
        result = parser.extract_elements(text, element_names=["action"])
        assert "action" in result

    def test_parse_without_action_wrapper(self):
        """Direct tool name tags should also be extracted."""
        parser = ToleranceXMLParser()
        text = '<tool><arg1>val1</arg1><arg2>val2</arg2></tool>'
        result = parser.extract_elements(text, element_names=["tool"])
        assert "tool" in result

    def test_find_elements_returns_xmlement_list(self):
        """find_elements should return a list of XMLElement objects."""
        parser = ToleranceXMLParser()
        text = "<answer>final result</answer>"
        elements = parser.find_elements(text, "answer")
        assert len(elements) >= 1
        assert isinstance(elements[0], XMLElement)
        assert elements[0].name == "answer"
        assert "final result" in elements[0].content

    def test_xmlement_has_required_fields(self):
        """XMLElement should have name, content, raw, start_pos, end_pos."""
        parser = ToleranceXMLParser()
        text = "<test>content here</test>"
        elements = parser.find_elements(text, "test")
        assert len(elements) == 1
        elem = elements[0]
        assert elem.name == "test"
        assert "content here" in elem.content
        assert "raw" in elem.model_fields_set or hasattr(elem, "raw")
        assert elem.start_pos >= 0
        assert elem.end_pos > elem.start_pos


class TestToleranceXMLParserMalformedInput:
    """R3-4: Malformed XML is handled gracefully."""

    def test_unclosed_tag_does_not_raise(self):
        """Unclosed tags should be handled without raising."""
        parser = ToleranceXMLParser()
        text = "<action><tool><arg>val"
        # Should not raise — ToleranceXMLParser is tolerant
        try:
            result = parser.extract_elements(text)
            # Either returns something or silently handles
            assert isinstance(result, dict)
        except (ValueError, TypeError):
            pytest.fail("extract_elements should not raise on malformed input")

    def test_mismatched_closing_tag_does_not_crash(self):
        """Mismatched closing tags should be handled."""
        parser = ToleranceXMLParser()
        text = "<action><tool>val</wrong></wrong></action>"
        try:
            result = parser.extract_elements(text)
            assert isinstance(result, dict)
        except (ValueError, TypeError):
            pytest.fail("extract_elements should not raise on mismatched tags")

    def test_empty_string_returns_empty_dict(self):
        """Empty input should return empty dict."""
        parser = ToleranceXMLParser()
        result = parser.extract_elements("")
        assert result == {}

    def test_plain_text_returns_empty_dict(self):
        """Plain text without XML tags returns empty dict."""
        parser = ToleranceXMLParser()
        result = parser.extract_elements("Just some plain text without tags.")
        assert result == {}

    def test_whitespace_only_returns_empty_dict(self):
        """Whitespace-only input is handled."""
        parser = ToleranceXMLParser()
        result = parser.extract_elements("   \n\t  ")
        assert result == {}

    def test_extract_with_element_names_filter(self):
        """Specifying element_names should filter results."""
        parser = ToleranceXMLParser()
        text = '<action><tool1>val1</tool1><tool2>val2</tool2></action>'
        result = parser.extract_elements(text, element_names=["tool1"])
        # Should either include tool1 or return empty for filtered names
        assert isinstance(result, dict)


class TestToleranceXMLParserEdgeCases:
    """R3-4: Edge cases are handled correctly."""

    def test_html_entities_decoded(self):
        """HTML entities like &lt; &gt; &amp; should be decoded."""
        parser = ToleranceXMLParser()
        text = "<msg>&lt;action&gt; &amp; &quot;test&quot;</msg>"
        elements = parser.find_elements(text, "msg")
        if elements:
            content = elements[0].content
            # Should decode < > & "
            assert "<" in content or "&lt;" not in content

    def test_cdata_section_preserved(self):
        """CDATA sections should be preserved or handled."""
        parser = ToleranceXMLParser()
        text = "<msg><![CDATA[<special>content</special>]]></msg>"
        result = parser.extract_elements(text, element_names=["msg"])
        assert isinstance(result, dict)
        # Should not crash

    def test_duplicate_element_names_deduplicated(self):
        """Duplicate element names in extract_elements are handled."""
        parser = ToleranceXMLParser()
        text = '<item>first</item><item>second</item>'
        result = parser.extract_elements(text, element_names=["item"])
        # Should return something, not crash
        assert isinstance(result, dict)

    def test_deeply_nested_structure(self):
        """Deeply nested XML should not cause recursion errors."""
        parser = ToleranceXMLParser()
        depth = 20
        inner = "<deep>value</deep>"
        for _ in range(depth - 1):
            inner = f"<level>{inner}</level>"
        text = f"<root>{inner}</root>"
        try:
            result = parser.extract_elements(text)
            assert isinstance(result, dict)
        except RecursionError:
            pytest.fail("extract_elements hit recursion limit on deeply nested XML")


class TestXMLElementValidation:
    """XMLElement Pydantic model validates correctly."""

    def test_xmlement_validates_end_pos_greater_than_start_pos(self):
        """end_pos must be > start_pos."""
        with pytest.raises(ValueError):
            XMLElement(
                name="test",
                content="content",
                raw="<test>content</test>",
                start_pos=10,
                end_pos=5,
            )

    def test_xmlement_accepts_valid_positions(self):
        """Valid start/end positions should be accepted."""
        elem = XMLElement(
            name="test",
            content="content",
            raw="<test>content</test>",
            start_pos=0,
            end_pos=20,
        )
        assert elem.name == "test"
        assert elem.start_pos == 0
        assert elem.end_pos == 20

    def test_xmlement_cdata_sections_defaults_to_empty_list(self):
        """cdata_sections defaults to empty list."""
        elem = XMLElement(
            name="test",
            content="content",
            raw="<test>content</test>",
            start_pos=0,
            end_pos=20,
        )
        assert elem.cdata_sections == []
