from ast import Dict
import functools
from typing import List, AnyStr
import asyncio

import aiocache

from src.utils.util import Util


class SearchSys:
    @classmethod
    @aiocache.cached(
        ttl=300, key_builder=lambda *args, **kwargs: Util.func_hash(*args, **kwargs)
    )
    async def get_file_paths(cls, root: str) -> Dict:
        abs_paths: List[str] = []
        Util.get_file_paths(abs_paths, root)

        return {path.split(root)[1]: path for path in abs_paths}

    @classmethod
    @aiocache.cached(
        ttl=600, key_builder=lambda *args, **kwargs: Util.func_hash(*args, **kwargs)
    )
    async def read_file(cls, abs_path):
        return await Util.sync_to_async(functools.partial(Util.read_txt, abs_path))

    @classmethod
    @aiocache.cached(
        ttl=600, key_builder=lambda *args, **kwargs: Util.func_hash(*args, **kwargs)
    )
    async def read_all(cls, paths: List[str]) -> List[List[str]]:
        """
        Reads all files in parallel!
        """

        contents = await asyncio.gather(*[cls.read_file(path) for path in paths])

        return {path: content for path, content in zip(paths, contents)}
