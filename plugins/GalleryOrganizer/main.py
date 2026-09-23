import json
import sys

from PythonDepManager import ensure_import

from graphql import GraphQLUtils

try:
    ensure_import("stashapi:stashapp-tools")
    ensure_import("bs4:beautifulsoup4")
except Exception as e:
    print(f"Error installing dependencies: {e}")

if __name__ == "__main__":
    info = json.loads(sys.stdin.read())
    mode = info.get("args", {}).get("mode")

    graphql_utils = GraphQLUtils(info.get("server_connection"))

    if mode == "galleries_title":
        graphql_utils.fill_galleries_title()
    elif mode == "galleries_date":
        graphql_utils.fill_galleries_date()
    elif mode == "galleries_urls":
        graphql_utils.sort_galleries_urls()
    elif mode == "galleries_performers":
        graphql_utils.add_galleries_performers()
    elif mode == "add_jvid_metadata":
        graphql_utils.add_jvid_metadata()
    elif mode == "add_xiuren_metadata":
        graphql_utils.add_xiuren_series_metadata()
