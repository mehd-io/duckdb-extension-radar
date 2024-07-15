import os
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

# Import your functions from the module where they are defined
from duckdb_extension_radar import run_graphql_query, search_github_repos


@pytest.fixture
def mock_response():
    """Prepare a mock response to mimic the GraphQL API."""
    return {
        "data": {
            "search": {
                "edges": [
                    {
                        "node": {
                            "name": "Repo1",
                            "url": "https://github.com/user/Repo1",
                            "description": "Description of Repo1",
                            "stargazers": {"totalCount": 42},
                            "createdAt": "2020-01-01T00:00:00Z",
                            "updatedAt": "2020-01-02T00:00:00Z",
                        }
                    }
                ],
                "pageInfo": {"endCursor": "abc123", "hasNextPage": False},
            }
        }
    }


@patch("requests.post")
def test_run_graphql_query(mock_post, mock_response):
    """Test the GraphQL query execution with dynamic token handling."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = mock_response
    token = os.getenv("GITHUB_TOKEN", "None")  # Fetch token or use "None" if not set

    query = "query { viewer { login }}"
    run_graphql_query(query)
    # Check that requests.post was called correctly, accounting for dynamic token
    mock_post.assert_called_once_with(
        "https://api.github.com/graphql",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def graphql_responses():
    """Simulate GraphQL responses for multiple pages."""
    return [
        {  # First page
            "data": {
                "search": {
                    "edges": [
                        {
                            "node": {
                                "name": "Repo1",
                                "url": "https://github.com/user/Repo1",
                                "description": "First repository",
                                "stargazers": {"totalCount": 10},
                                "createdAt": "2021-01-01T00:00:00Z",
                                "updatedAt": "2021-01-02T00:00:00Z",
                            },
                            "cursor": "cursor1",
                        }
                    ],
                    "pageInfo": {"endCursor": "cursor1", "hasNextPage": True},
                }
            }
        },
        {  # Second page
            "data": {
                "search": {
                    "edges": [
                        {
                            "node": {
                                "name": "Repo2",
                                "url": "https://github.com/user/Repo2",
                                "description": "Second repository",
                                "stargazers": {"totalCount": 20},
                                "createdAt": "2022-02-01T00:00:00Z",
                                "updatedAt": "2022-02-02T00:00:00Z",
                            },
                            "cursor": "cursor2",
                        }
                    ],
                    "pageInfo": {"endCursor": "cursor2", "hasNextPage": False},
                }
            }
        },
    ]


@patch("duckdb_extension_radar.run_graphql_query")
def test_search_github_repos(mock_run_query, graphql_responses):
    """Test the repository search and pagination handling."""
    mock_run_query.side_effect = (
        graphql_responses  # Use side_effect to simulate sequence of responses
    )

    result_df = search_github_repos("dummy_extension")

    # Define what the expected DataFrame should look like
    expected_df = pd.DataFrame(
        {
            "Repository": ["Repo1", "Repo2"],
            "Url": ["https://github.com/user/Repo1", "https://github.com/user/Repo2"],
            "About": ["First repository", "Second repository"],
            "Stars": [10, 20],
            "Created": ["2021-01-01T00:00:00Z", "2022-02-01T00:00:00Z"],
            "Last Updated": ["2021-01-02T00:00:00Z", "2022-02-02T00:00:00Z"],
        }
    )

    pd.testing.assert_frame_equal(result_df, expected_df)
