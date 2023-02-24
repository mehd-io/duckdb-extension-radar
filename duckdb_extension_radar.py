import os
from datetime import date
from typing import Dict, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_search_results(query: str, filename: Optional[str] = None) -> Dict:
    # Search for repositories containing the query string in the code
    # if filename is empty do not put it in the query
    if filename is None:
        url = f"https://api.github.com/search/code?q={query}"
    else:
        url = f"https://api.github.com/search/code?q={query}+filename:{filename}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    response_json = response.json()
    if "items" not in response_json:
        raise ValueError("The search query did not return any results")
    return response_json


def get_repository_info(repo_url: str, headers: Dict) -> Dict:
    repo_response = requests.get(repo_url, headers=headers)
    repo_json = repo_response.json()
    repo_dict = {
        "Repository": repo_json["html_url"],
        "About": repo_json["description"],
        "Stars": repo_json["stargazers_count"],
    }

    # Get information about the repository
    repo_info_url = repo_json["url"]
    repo_info_response = requests.get(repo_info_url, headers=headers)
    repo_info_json = repo_info_response.json()
    repo_dict["Created"] = repo_info_json["created_at"]
    repo_dict["Last Commit"] = repo_info_json["pushed_at"]

    return repo_dict


def get_contributors(contributors_url: str, headers: Dict) -> str:
    contributors_response = requests.get(contributors_url, headers=headers)
    contributors_json = contributors_response.json()
    contributors_list = [contributor["login"] for contributor in contributors_json]
    return ", ".join(contributors_list)


def search_github_repos(query: str, filename: Optional[str] = None) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response_json = get_search_results(query, filename)

    repos = []
    for item in response_json["items"]:
        repo_url = item["repository"]["url"]
        repo_dict = get_repository_info(repo_url, headers)
        contributors_url = repo_dict.get("contributors_url")
        if contributors_url:
            repo_dict["Contributors (Username)"] = get_contributors(
                contributors_url, headers
            )
        repos.append(repo_dict)

    return pd.DataFrame(repos)


def generate_readme(df: pd.DataFrame):
    # Generate a nice table in Markdown format
    table_md = df.to_markdown(index=False)
    # Add header and description
    header = "# DuckDB Extensions Radar\n"
    header += "![DuckDB Extensions Radar](/img/duckdb_extensions_radar.pn?raw=true)\n"
    description = f'This repo contains information about DuckDB extensions found on GitHub. Refreshed daily. Last refresh **{date.today().strftime("%Y-%m-%d")}**.'
    readme_md = f"{header}{description}\n\n{table_md}"
    # Write the README file
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_md)


if __name__ == "__main__":
    # Query for repositories containing the query string in the code
    # For some reasons, the search API does not return all the results when not filtering on some specific files
    # So we do two searches, one for the query string in all files and one for the query string in the yml files
    df_wide_search = search_github_repos(query=".duckdb_extension")
    df_yml = search_github_repos(query=".duckdb_extension", filename="yml")
    # merge the two dataframes
    df = pd.concat([df_wide_search, df_yml], ignore_index=True)
    # order by created date
    df = df.sort_values(by="Created", ascending=False)
    # remove duplicates
    df = df.drop_duplicates(subset="Repository", keep="first")
    # generate the readme
    generate_readme(df)
