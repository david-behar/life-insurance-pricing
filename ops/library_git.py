"""Link the Dataiku project library to this GitHub repo, or pull the latest engine.

Run with the Python that ships with the dku CLI (it has dataikuapi and dku's credentials):

    ~/.local/share/uv/tools/dku-cli/bin/python3 ops/library_git.py link
    ~/.local/share/uv/tools/dku-cli/bin/python3 ops/library_git.py pull
"""
import sys

from dku_cli.client import get_client

PROJECT_KEY = "SAVINGS_PRICING_DEMO"
REPOSITORY = "https://github.com/david-behar/life-insurance-pricing.git"
BRANCH = "main"
PATH_IN_REPO = "python"
LIBRARY_PATH = "savings_pricing_engine"


def main(action):
    git = get_client().get_project(PROJECT_KEY).get_project_git()
    if action == "link":
        git.add_library(REPOSITORY, LIBRARY_PATH, BRANCH, path_in_git_repository=PATH_IN_REPO,
                        add_to_python_path=True)
    elif action == "pull":
        git.reset_library(LIBRARY_PATH)
    else:
        sys.exit("usage: library_git.py link|pull")
    for ref in git.list_libraries():
        print(ref)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
