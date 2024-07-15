import os
from datetime import date

import pandas as pd
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def run_graphql_query(query: str):
    """Helper function to run a GraphQL query using requests"""
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {response.text}"
        )


def search_github_repos(extension: str):
    """Perform a paginated GraphQL search for repositories containing files with the specific extension"""
    repos = []
    has_next_page = True
    cursor = None  # Start with no cursor
    page_count = 0

    while has_next_page:
        page_count += 1
        pagination_part = f', after: "{cursor}"' if cursor else ""
        query = f"""
        query {{
          search(query: "extension:{extension}", type: REPOSITORY, first: 10{pagination_part}) {{
            edges {{
              cursor
              node {{
                ... on Repository {{
                  name
                  url
                  description
                  stargazers {{
                    totalCount
                  }}
                  createdAt
                  updatedAt
                }}
              }}
            }}
            pageInfo {{
              endCursor
              hasNextPage
            }}
          }}
        }}
        """
        result = run_graphql_query(query)
        edges = result["data"]["search"]["edges"]
        for edge in edges:
            repos.append(
                {
                    "Repository": edge["node"]["name"],
                    "Url": edge["node"]["url"],
                    "About": edge["node"]["description"],
                    "Stars": edge["node"]["stargazers"]["totalCount"],
                    "Created": edge["node"]["createdAt"],
                    "Last Updated": edge["node"]["updatedAt"],
                }
            )
        page_info = result["data"]["search"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]

        if has_next_page:
            logger.info(
                f"Fetching next page of results, total pages: {page_count}, total repositories fetched: {len(repos)}"
            )

    logger.info(
        f"Total pages processed: {page_count}, Total repositories found: {len(repos)}"
    )
    return pd.DataFrame(repos)


def generate_readme(df: pd.DataFrame):
    # Transform the Repository column into a markdown link string using the Url column
    df["Repository"] = df.apply(
        lambda row: f"[{row['Repository']}]({row['Url']})", axis=1
    )
    # Select the columns to display
    df = df[
        [
            "Repository",
            "Stars",
            "Created",
            "Last Updated",  # Updated to reflect actual data column name from GraphQL
            "About",
        ]
    ]
    # Sort by Last Updated date
    sorted_df = df.copy()
    sorted_df.sort_values(by='Last Updated', ascending=False, inplace=True)
    # Generate a nice table in Markdown format
    table_md = sorted_df.to_markdown(index=False)
    # Add header and description
    header = "![DuckDB Extensions Radar](/img/duckdb_extension_radar.png?raw=true)\n"
    header += "# DuckDB Extensions Radar\n"
    description = f'\nThis repo contains information about DuckDB extensions found on GitHub. Refreshed daily. Sorted by Created date. \n Last refresh **{date.today().strftime("%Y-%m-%d")}**.'
    warning = "## ⚠️ Disclaimer\nThis is a bit hacky and searches for repos containing the string `.duckdb_extension`, so it's not 100% reliable.\nExtensions that are not included in the DuckDB core (and are not listed in the output from duckdb_extensions()) are considered unsigned. To install these extensions, you must use the `-unsigned` flag when launching DuckDB. Please be aware that installing unsigned extensions carries potential risks, as this repository does not endorse or guarantee the trustworthiness of any listed extensions."
    readme_md = f"{header}{description}\n{warning}\n{table_md}"
    # Write the README file
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_md)


if __name__ == "__main__":
    logger.info("Starting the search for repositories with .duckdb_extension files")
    df = search_github_repos("duckdb_extension")
    logger.info("Generating the README file")
    generate_readme(df)
