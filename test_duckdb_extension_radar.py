from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from pandas import DataFrame

from duckdb_extension_radar import (get_contributors, get_repository_info,
                                    get_search_results)


@pytest.fixture
def search_results_mock():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {"repository": {"url": "https://api.github.com/repos/octocat/Hello-World"}},
            {
                "repository": {
                    "url": "https://api.github.com/repos/octocat/Another-Repo"
                }
            },
        ]
    }
    return mock_response


@pytest.fixture
def repository_info_mock():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "full_name": "octocat/Hello-World",
        "html_url": "https://github.com/octocat/Hello-World",
        "description": "This is a description",
        "stargazers_count": 100,
        "url": "https://api.github.com/repos/octocat/Hello-World",
        "created_at": "2022-01-01T00:00:00Z",
        "pushed_at": "2022-01-10T00:00:00Z",
        "contributors_url": "https://api.github.com/repos/octocat/Hello-World/contributors",
    }
    return mock_response


@pytest.fixture
def contributors_mock():
    mock_response = MagicMock()
    mock_response.json.return_value = [{"login": "user1"}, {"login": "user2"}]
    return mock_response


@patch("requests.get")
def test_get_search_results(mock_get, search_results_mock):
    mock_get.return_value = search_results_mock
    response = get_search_results("query")
    assert response == search_results_mock.json()


@patch("requests.get")
def test_get_repository_info(mock_get, repository_info_mock):
    mock_get.return_value = repository_info_mock
    headers = {"Authorization": "Bearer token"}
    response = get_repository_info(
        "https://api.github.com/repos/octocat/Hello-World", headers
    )
    assert response == {
        "Repository": "octocat/Hello-World",
        "Url": "https://github.com/octocat/Hello-World",
        "About": "This is a description",
        "Stars": 100,
        "Created": "2022-01-01T00:00:00Z",
        "Last Commit": "2022-01-10T00:00:00Z",
    }


@patch("requests.get")
def test_get_contributors(mock_get, contributors_mock):
    mock_get.return_value = contributors_mock
    headers = {"Authorization": "Bearer token"}
    response = get_contributors(
        "https://api.github.com/repos/octocat/Hello-World/contributors", headers
    )
    assert response == "user1, user2"
