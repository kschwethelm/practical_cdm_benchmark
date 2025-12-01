"""Unit tests for agent.py - LLM agent building and tool validation."""

from unittest.mock import Mock

import pytest

from cdm.llms.agent import build_agent


class TestBuildAgent:
    """Test suite for build_agent function and tool validation."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock ChatOpenAI instance."""
        return Mock()

    @pytest.fixture
    def sample_case(self):
        """Create a minimal sample case for testing."""
        return {
            "hadm_id": 12345,
            "demographics": {"age": 65, "gender": "M"},
            "history_of_present_illness": "Test patient info",
            "ground_truth": {"primary_diagnosis": "Test diagnosis"},
            "physical_exam_text": "Normal examination",
            "lab_results": [],
            "microbiology_events": [],
            "radiology_reports": [],
        }

    def test_build_agent_with_valid_tools(self, mock_llm, sample_case):
        """Test that build_agent succeeds with all valid tool names."""
        valid_tools = ["physical_exam", "lab", "microbiology", "radiology"]
        agent = build_agent(mock_llm, valid_tools)
        assert agent is not None

    def test_build_agent_with_subset_of_tools(self, mock_llm, sample_case):
        """Test that build_agent works with a subset of available tools."""
        subset_tools = ["physical_exam", "lab"]
        agent = build_agent(mock_llm, subset_tools)
        assert agent is not None

    def test_build_agent_with_empty_tools(self, mock_llm, sample_case):
        """Test that build_agent works with no tools enabled."""
        agent = build_agent(mock_llm, [])
        assert agent is not None

    def test_build_agent_raises_error_on_invalid_tool(self, mock_llm, sample_case):
        """Test that build_agent raises ValueError for invalid tool names."""
        invalid_tools = ["physical_exam", "invalid_tool"]

        with pytest.raises(ValueError):
            build_agent(mock_llm, invalid_tools)

    def test_build_agent_raises_error_on_multiple_invalid_tools(self, mock_llm, sample_case):
        """Test that build_agent lists all invalid tools in error message."""
        invalid_tools = ["invalid_tool1", "invalid_tool2", "physical_exam"]

        with pytest.raises(ValueError):
            build_agent(mock_llm, invalid_tools)
