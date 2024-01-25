import asyncio
import copy
import datetime
import os
import sys
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from typing import Dict, List, Optional

from starlette.websockets import WebSocket
from src.core.search_sys import SearchSys
from src.utils.config import Config
from src.utils.util import Util
from src.web.web_util import WebUtil

app = FastAPI()


def make_dict_jsonable(input_dict: Dict):
    ret = copy.deepcopy(input_dict)

    for k, v in ret.items():
        if k == "time":
            if isinstance(v, datetime.datetime):
                ret[k] = str(v)
            elif isinstance(v, list):
                ret[k] = [str(t) for t in v]

    return ret


@app.get("/search")
@app.post("/search")
async def normal_search(request: Request):
    try:
        start_time = Util.time_now()

        body = await WebUtil.get_params(request)

        WebUtil.ensure_valid_request(body, "keyword")
        keyword = Util.read_map_value(body, "keyword", "no_keyword")
        n_threads = int(Util.read_map_value(body, "n_threads", "128"))

        sources: List[Dict] = Config.get_config_param("sources", [])

        ret = []

        # Iterate through each source
        for s in sources:
            local: str = s["source"]
            remote: str = s["remote"]
            is_jekyll: bool = Util.read_map_value(s, "jekyll", False)
            extension: Optional[List[str]] = Util.read_map_value(s, "extension", None)

            if not local.startswith("/"):  # Relative Path
                local = Util.get_abs_path(local)

            results = await SearchSys.find_in_files(
                local, keyword, n_threads=n_threads, file_extensions=extension
            )

            ret += [
                {
                    **r,
                    # Support jekyll
                    "remote_path": (remote + r["path"])
                    if not is_jekyll
                    else (remote + r["path"]).replace(
                        # Extension
                        "." + r["path"].split(".")[-1],
                        # Jekyll's param ending
                        ".html?print-pdf#/",
                    ),
                    "source": s["name"],
                }
                for r in results
            ]

        ret.sort(key=lambda entry: entry["priority"])

        return WebUtil.make_success(
            {
                "elapsed_time": Util.get_elapsed_time_ms_str(start_time),
                "matches": ret,
            }
        )

    except Exception as e:
        Util.error(e)
        return WebUtil.make_error(e)


def start_server(host: str = "0.0.0.0", port: int = 3000):
    global app

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  #
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Util.info(f"Naive-doc-search is alive at address {host}:{port}!")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    port = Config.get_config_param("port", 3000, int)

    start_server(port=port)
