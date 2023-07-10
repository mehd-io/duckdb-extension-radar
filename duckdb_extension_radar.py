import os
from datetime import date
from typing import Dict, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_search_results(
    query: str, filename: Optional[str] = None, page: int = 1, per_page: int = 100
) -> Dict:
    if filename is None:
        url = f"https://api.github.com/search/code?q={query}&page={page}&per_page={per_page}"
    else:
        url = f"https://api.github.com/search/code?q={query}+filename:{filename}&page={page}&per_page={per_page}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    logger.info(
        f"Requested search results for query: {query}, page: {page}, per_page: {per_page}"
    )
    response_json = response.json()

    if "total_count" not in response_json:
        logger.error(f"Unexpected response from GitHub API: {response_json}")
        raise ValueError("The search query returned an unexpected response")

    if response_json["total_count"] == 0:
        raise ValueError("The search query did not return any results")

    return response_json


def search_github_repos(
    query: str, filename: Optional[str] = None, max_pages: int = 10
) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    repos = []
    repo_urls = set()
    page = 1
    while True:
        response_json = get_search_results(query, filename, page)
        for item in response_json.get("items", []):
            repo_urls.add(item["repository"]["url"])

        if not response_json["items"] or page > max_pages:
            break

        page += 1

    logger.info(
        f"Finished searching GitHub repos, total repositories found: {len(repo_urls)}"
    )

    # Populate repos with data from the repo url since the response from the
    # search API does not contain all the data.
    for url in repo_urls:
        repos.append(get_repository_info(url, headers))

    # This isn't currently used
    # for repo in repos:
    #     contributors_url = repo.get("contributors_url")
    #     if contributors_url:
    #         repo["Contributors"] = get_contributors(contributors_url, headers)
    return pd.DataFrame(repos)


def get_repository_info(repo_url: str, headers: Dict) -> Dict:
    repo_response = requests.get(repo_url, headers=headers)
    repo_json = repo_response.json()
    if "full_name" not in repo_json:
        logger.error(
            f"Unexpected response from GitHub API for repo {repo_url}: {repo_json}"
        )
        return {}
    repo_dict = {
        "Repository": repo_json["full_name"],
        "Url": repo_json["html_url"],
        "About": repo_json["description"],
        "Stars": repo_json["stargazers_count"],
        "Created": repo_json["created_at"],
        "Last Commit": repo_json["pushed_at"],
    }

    return repo_dict


def get_contributors(contributors_url: str, headers: Dict) -> str:
    contributors_response = requests.get(contributors_url, headers=headers)
    contributors_json = contributors_response.json()
    contributors_list = [contributor["login"] for contributor in contributors_json]
    return ", ".join(contributors_list)


def generate_readme(df: pd.DataFrame):
    # Transform the Repository column into a markdown link string using the Url column
    df["Repository"] = df.apply(
        lambda row: f"[{row['Repository']}]({row['Url']})", axis=1
    )
    # select the columns to display
    df = df[
        [
            "Repository",
            "Stars",
            "Created",
            "Last Commit",
            "About",
        ]
    ]
    # Generate a nice table in Markdown format
    table_md = df.to_markdown(index=False)
    # Add header and description
    header = "![DuckDB Extensions Radar](/img/duckdb_extension_radar.png?raw=true)\n"
    header += "# DuckDB Extensions Radar\n"
    description = f'\nThis repo contains information about DuckDB extensions found on GitHub. Refreshed daily. Sorted by Created date. \n Last refresh **{date.today().strftime("%Y-%m-%d")}**.'
    warning = "## ⚠️ Disclaimer\n This a bit hacky and searching for repos containing the string `.duckdb_extension`. so not 100% reliable.\n Extensions that are not included in the DuckDB core (and are not listed in the output of from duckdb_extensions()) are considered unsigned. To install these extensions, you must use the -unsigned flag when launching DuckDB. Please be aware that installing unsigned extensions carries potential risks, as this repository does not endorse or guarantee the trustworthiness of any listed extensions."
    readme_md = f"{header}{description}\n{warning}\n{table_md}"
    # Write the README file
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_md)


if __name__ == "__main__":
    # Query for repositories containing the query string in the code
    # For some reasons, the search API does not return all the results when not filtering on some specific files
    # So we do two searches, one for the query string in all files and one for the query string in the yml files
    logger.info("Starting the search for DuckDB extensions")
    df_wide_search = search_github_repos(query=".duckdb_extension")
    df_yml = search_github_repos(query=".duckdb_extension", filename="yml")
    # merge the two dataframes
    df = pd.concat([df_wide_search, df_yml], ignore_index=True)
    # order by created date
    df = df.sort_values(by="Created", ascending=False)
    # remove duplicates
    df = df.drop_duplicates(subset="Repository", keep="first")
    # generate the readme
    logger.info("Generating the README file")
    generate_readme(df)
