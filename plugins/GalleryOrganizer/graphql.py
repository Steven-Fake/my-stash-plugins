import re
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import stashapi.log as log
from stashapi.stashapp import StashInterface


def log_wrapper(func: Callable):
    def wrapper(*args, **kwargs):
        quiet = kwargs.get("quiet", False)
        if not quiet:
            log.info(f"Starting {func.__name__.replace('_', ' ').capitalize()}...")
        result = func(*args, **kwargs)
        if not quiet:
            log.info(f"Completed {func.__name__.replace('_', ' ').capitalize()}.")
        return result

    return wrapper


class GraphQLUtils:
    def __init__(self, config: dict):
        self.client = StashInterface(config)

    @log_wrapper
    def fill_galleries_title(self, quiet: bool = False):
        resp = self.client.find_galleries(
            f={"title": {"value": "", "modifier": "IS_NULL"}},
            fragment="id files { basename } folder { path }",
        )
        total = len(resp)
        if not quiet:
            log.info(f"Found {total} galleries without title")
        for i, item in enumerate(resp):
            if not quiet:
                log.progress(i / total)
            gallery_id: str = item.get("id")
            if (item.get("folder") or {}).get("path", ""):
                title = Path(item.get("folder").get("path")).name
            elif len(item.get("files", [])) > 0:
                zip_name = item.get("files", [])[0].get("basename", "")
                title = zip_name[: zip_name.rindex(".")]
            else:
                continue
            self.client.update_gallery({"id": gallery_id, "title": title})

    @log_wrapper
    def fill_galleries_date(self, quiet: bool = False):
        self.fill_galleries_title(quiet=True)
        resp = self.client.find_galleries(
            f={
                "date": {"value": "", "modifier": "IS_NULL"},
                "title": {
                    "value": "\\d{4}([-.])(0[1-9]|1[0-2])(?:(0[1-9]|[12]\\d|3[01]))?",
                    "modifier": "MATCHES_REGEX",
                },
            },
            fragment="id title",
        )
        total = len(resp)
        if not quiet:
            log.info(f"Found {total} galleries without date")
        for i, item in enumerate(resp):
            if not quiet:
                log.progress(i / total)
            date_match = re.search(
                r"\d{4}([-.])(0[1-9]|1[0-2])(?:([-.])?(0[1-9]|[12]\d|3[01]))?",
                item.get("title"),
            )
            if date_match:
                date_str = date_match.group()
                date = date_str.replace(".", "-")
                self.client.update_gallery({"id": item.get("id"), "date": date})

    @log_wrapper
    def add_galleries_performers(self, quiet: bool = False):
        self.fill_galleries_title(quiet=True)
        resp = self.client.find_galleries(
            f={"performer_count": {"value": 0, "modifier": "EQUALS"}},
            fragment="id title",
        )
        total = len(resp)
        if not quiet:
            log.info(f"Found {total} galleries without performers")
        for i, item in enumerate(resp):
            if not quiet:
                log.progress(i / total)
            gallery_id: str = item.get("id")
            performer_names = [
                name.strip() for name in item.get("title").split("_")[-1].split(",")
            ]
            performer_ids = []
            for name in performer_names:
                performer_resp = self.client.find_performers(
                    q=name, fragment="""id name alias_list"""
                )
                if performer_resp:
                    for performer in performer_resp:
                        if name == performer.get("name") or name in performer.get(
                            "alias_list", []
                        ):
                            performer_ids.append(performer.get("id"))
            if performer_ids:
                self.client.update_gallery(
                    {"id": gallery_id, "performer_ids": performer_ids}
                )

    @log_wrapper
    def add_jvid_metadata(self, quiet: bool = False):
        resp = self.client.find_galleries(
            f={
                "title": {"value": "^\\[写真\\]JVID", "modifier": "MATCHES_REGEX"},
            },
            fragment="id title code",
        )

        total = len(resp)
        if not quiet:
            log.info(f"Found {total} JVID galleries to sort")
        for i, item in enumerate(resp):
            if not quiet:
                log.progress(i / total)

            title: str = item.get("title", "")
            search_result = re.search(r"_([\w\d]+)_", title)
            if not search_result:
                continue
            code = search_result.group(1)
            url = f"https://www.jvid.com/v/{code}"

            self.client.update_gallery(
                {"id": item.get("id"), "code": code, "urls": [url]}
            )

    @log_wrapper
    def add_xiuren_series_metadata(self, quiet: bool = False):
        uncensored_search = self.client.find_tags(
            f={"aliases": {"value": "Uncensored", "modifier": "EQUALS"}}
        )
        uncensored_tag_id: str | None = (
            uncensored_search[0].get("id") if uncensored_search else None
        )

        studios = [
            "FEILIN",
            "HUAYANG",
            "IMISS",
            "MYGIRL",
            "XIAOYU",
            "XINGYAN",
            "XIUREN",
            "YOUMI",
            "TUIGIRL",
            "UGIRL",
        ]
        resp = self.client.find_galleries(
            f={
                "title": {
                    "value": f"^\\[写真\\]({'|'.join(studios)})",
                    "modifier": "MATCHES_REGEX",
                }
            },
            fragment="id title code tags { id }",
        )

        total = len(resp)
        if not quiet:
            log.info(f"Found {total} XIUREN series galleries to sort")
        for i, item in enumerate(resp):
            if not quiet:
                log.progress(i / total)
            title: str = item.get("title", "")
            tag_ids = [t.get("id") for t in item.get("tags", [])]
            search_result = re.search(r"((Vol|No)\.\d+)", title)
            if not search_result:
                continue
            code = search_result.group(1)
            if "Uncensored" in title and uncensored_tag_id:
                tag_ids.append(uncensored_tag_id)

            self.client.update_gallery(
                {"id": item.get("id"), "code": code, "tag_ids": tag_ids}
            )
