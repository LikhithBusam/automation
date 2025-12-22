"""
Test suite to verify GroupChat termination fix

This test verifies that the GroupChatManager properly terminates
conversations when termination keywords are detected.
"""

import pytest
import logging
from pathlib import Path
from src.autogen_adapters.groupchat_factory import GroupChatFactory


@pytest.fixture
def groupchat_factory():
    """Create a GroupChatFactory instance"""
    config_path = "config/autogen_groupchats.yaml"
    return GroupChatFactory(config_path)


def test_termination_function_creation(groupchat_factory):
    """Test that termination functions are created correctly"""
    # Test code review termination
    termination_func = groupchat_factory._create_termination_function("check_code_review_complete")

    assert termination_func is not None, "Termination function should be created"

    # Test with TERMINATE keyword
    msg1 = {"content": "Analysis complete. TERMINATE"}
    assert termination_func(msg1) == True, "Should detect TERMINATE keyword"

    # Test with CODE_REVIEW_COMPLETE keyword
    msg2 = {"content": "All issues addressed. CODE_REVIEW_COMPLETE"}
    assert termination_func(msg2) == True, "Should detect CODE_REVIEW_COMPLETE keyword"

    # Test case insensitivity
    msg3 = {"content": "done terminate"}
    assert termination_func(msg3) == True, "Should be case insensitive"

    # Test non-termination message
    msg4 = {"content": "Let's continue the analysis"}
    assert termination_func(msg4) == False, "Should not terminate on normal message"


def test_multiple_terminate_detection(groupchat_factory):
    """Test detection of multiple TERMINATE messages (infinite loop scenario)"""
    termination_func = groupchat_factory._create_termination_function("check_code_review_complete")

    # Simulate the infinite loop scenario from the error log
    msg_with_multiple_terminates = {
        "content": """**TERMINATE**
**TERMINATE**
**TERMINATE**
**TERMINATE**
**TERMINATE**"""
    }

    assert termination_func(msg_with_multiple_terminates) == True, \
        "Should detect multiple TERMINATE messages and force termination"


def test_empty_or_none_content(groupchat_factory):
    """Test handling of empty or None content"""
    termination_func = groupchat_factory._create_termination_function("check_code_review_complete")

    # Test empty content
    msg1 = {"content": ""}
    assert termination_func(msg1) == False, "Should not terminate on empty content"

    # Test None content
    msg2 = {"content": None}
    assert termination_func(msg2) == False, "Should not terminate on None content"

    # Test missing content key
    msg3 = {}
    assert termination_func(msg3) == False, "Should not terminate on missing content"


def test_all_termination_conditions(groupchat_factory):
    """Test all configured termination conditions"""
    conditions = [
        "check_code_review_complete",
        "check_security_audit_complete",
        "check_documentation_complete",
        "check_deployment_complete",
        "check_research_complete",
        "check_full_team_complete"
    ]

    for condition_name in conditions:
        termination_func = groupchat_factory._create_termination_function(condition_name)
        assert termination_func is not None, f"Should create termination function for {condition_name}"

        # Test TERMINATE keyword (common to all)
        msg = {"content": "TERMINATE"}
        assert termination_func(msg) == True, \
            f"Termination function for {condition_name} should detect TERMINATE"


def test_groupchat_configs_have_termination_conditions(groupchat_factory):
    """Verify all groupchats have termination conditions configured"""
    groupchats = groupchat_factory.groupchat_configs

    for chat_name, chat_config in groupchats.items():
        assert "termination_condition" in chat_config, \
            f"GroupChat {chat_name} should have termination_condition configured"

        condition_name = chat_config["termination_condition"]
        assert condition_name in groupchat_factory.termination_configs, \
            f"Termination condition {condition_name} should be defined"


def test_security_audit_termination_keywords(groupchat_factory):
    """Test security audit specific termination keywords"""
    termination_func = groupchat_factory._create_termination_function("check_security_audit_complete")

    # Test specific keywords
    keywords = [
        "SECURITY_AUDIT_COMPLETE",
        "NO_VULNERABILITIES_FOUND",
        "TERMINATE"
    ]

    for keyword in keywords:
        msg = {"content": f"Analysis complete: {keyword}"}
        assert termination_func(msg) == True, \
            f"Should detect security audit keyword: {keyword}"


def test_documentation_termination_keywords(groupchat_factory):
    """Test documentation generation specific termination keywords"""
    termination_func = groupchat_factory._create_termination_function("check_documentation_complete")

    keywords = [
        "DOCUMENTATION_COMPLETE",
        "DOCS_GENERATED",
        "TERMINATE"
    ]

    for keyword in keywords:
        msg = {"content": f"{keyword} - all docs ready"}
        assert termination_func(msg) == True, \
            f"Should detect documentation keyword: {keyword}"


def test_deployment_termination_keywords(groupchat_factory):
    """Test deployment workflow termination keywords"""
    termination_func = groupchat_factory._create_termination_function("check_deployment_complete")

    keywords = [
        "DEPLOYMENT_COMPLETE",
        "DEPLOYMENT_SUCCESS",
        "DEPLOYMENT_FAILED",
        "TERMINATE"
    ]

    for keyword in keywords:
        msg = {"content": f"Status: {keyword}"}
        assert termination_func(msg) == True, \
            f"Should detect deployment keyword: {keyword}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
