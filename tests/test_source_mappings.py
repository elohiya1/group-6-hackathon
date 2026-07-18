import pytest

from memory_layer.source_mappings import extract_field, load_source_mapping


def test_load_github_mapping():
    mapping = load_source_mapping("github")
    assert mapping.identifiers[0].raw_field == "owner.login"
    assert mapping.identifiers[0].identifier_type == "github_username"
    assert mapping.attributes[0].raw_field == "stargazers_count"
    assert mapping.attributes[0].attribute_name == "github_stars"


def test_load_tavily_mapping_has_two_identifiers():
    mapping = load_source_mapping("tavily")
    identifier_types = {i.identifier_type for i in mapping.identifiers}
    assert identifier_types == {"company_domain", "email"}


def test_load_unknown_source_raises():
    with pytest.raises(KeyError):
        load_source_mapping("not_a_real_source")


def test_extract_field_nested():
    payload = {"owner": {"login": "octocat"}, "stargazers_count": 1200}
    assert extract_field(payload, "owner.login") == "octocat"
    assert extract_field(payload, "stargazers_count") == 1200


def test_extract_field_missing_returns_none():
    payload = {"owner": {}}
    assert extract_field(payload, "owner.login") is None
    assert extract_field(payload, "nonexistent") is None
