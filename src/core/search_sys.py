from ast import Dict
import functools
import string
from typing import List, AnyStr, Optional
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
    async def read_all(cls, paths: List[str]) -> Dict:
        """
        Reads all files in parallel!
        """

        contents = await asyncio.gather(*[cls.read_file(path) for path in paths])

        return {path: content for path, content in zip(paths, contents)}

    @classmethod
    def find_in_file(
        cls, keyword: str, lines: List[str], context_length: 32, path: Optional[str]
    ) -> List[Dict]:
        ret = []

        # Delete empty lines
        lines = [line for line in lines if len(line.strip()) > 0]
        full_doc = "\n".join(lines)
        sz_lines = len(lines)

        # Attempt to parse title
        title = path

        # Jekyll Markdown?
        if path.endswith(".markdown") or path.endswith(".md"):
            has_dashes_once = False

            for ind in range(len(lines)):
                line = lines[ind]

                if line.startswith("---"):
                    if has_dashes_once:
                        break

                    has_dashes_once = True

                # Extract page title if found
                if line.startswith("title: "):
                    title = line.split("title: ")[-1]
                    break
        elif path.endswith(".html"):
            # Let's extract <head> content
            start_index = full_doc.find("<head>") + len("<head>")
            end_index = full_doc.find("</head>")

            # Extract lines belonging to the head
            head_content = full_doc[start_index:end_index].strip()

            # Now look for title
            start_index = full_doc.find("<title>") + len("<title>")
            end_index = full_doc.find("</title>")

            # If there is indeed a title set, grab it!
            if end_index != -1:
                title = full_doc[start_index:end_index].strip()

        chunks = []

        # Group lines into chunks
        for i in range(0, sz_lines, context_length):
            if i >= sz_lines:
                break
            chunks.append("\n".join(lines[i : min(sz_lines, i + context_length)]))

        lower_chunks = [chunk.lower() for chunk in chunks]
        lower_keyword = keyword.lower()
        idxes = [i for i in range(len(chunks))]

        for idx, lower, raw in zip(idxes, lower_chunks, chunks):
            # Case sensitive
            if keyword in raw:
                ret.append(
                    {
                        "type": "exact",
                        "title": title,
                        "keyword": keyword,
                        "input_keyword": keyword,
                        "chunk": raw.split("\n"),
                        "priority": 0,
                        "path": path or "anonymous",
                    }
                )
            # Case insensitive
            elif lower_keyword in lower:
                ret.append(
                    {
                        "type": "bad_case",
                        "title": title,
                        "keyword": lower_keyword,
                        "input_keyword": keyword,
                        "chunk": raw.split("\n"),
                        "priority": 1,
                        "path": path or "anonymous",
                    }
                )
            # Disable subset search since it is NOT reliable
            # else:
            #     space_only = str.maketrans("", "", string.punctuation)
            #     broken_keys = [
            #         key.lower() for key in keyword.translate(space_only).split()
            #     ]

            #     for key in broken_keys:
            #         if key in lower:
            #             ret.append(
            #                 {
            #                     "type": "subset",
            #                     "title": title,
            #                     "keyword": key,
            #                     "input_keyword": keyword,
            #                     "chunk": raw.split("\n"),
            #                     "priority": 1,
            #                     "path": path or "anonymous",
            #                 }
            #             )

        return ret

    @classmethod
    async def find_in_files(
        cls,
        root: str,
        keyword: str,
        n_threads=128,
        file_extensions: Optional[List[str]] = None,
    ) -> List[Dict]:
        ret = []
        file_map = await cls.get_file_paths(root)

        # Filter by file extension
        if file_extensions is not None:
            file_extensions = set(file_extensions)
            file_map = {
                k: v
                for k, v in file_map.items()
                if ("." in v) and (v.split(".")[-1] in file_extensions)
            }

        # List of relative paths
        file_list = list(file_map.keys())
        sz_list = len(file_list)

        for i in range(0, sz_list, n_threads):
            if i >= sz_list:
                break

            # Now 'chunk' contains a subset of the original list with at most 128 elements
            chunk = file_list[i : min(i + n_threads, sz_list)]

            files = await cls.read_all(
                [file_map[relative_path] for relative_path in chunk]
            )

            coroutines = [
                Util.sync_to_async(
                    functools.partial(
                        cls.find_in_file,
                        keyword=keyword,
                        lines=lines,
                        context_length=4,
                        path=path,
                    )
                )
                for path, lines in zip(chunk, list(files.values()))
            ]

            chunk_res: List[List[Dict]] = await asyncio.gather(*coroutines)

            for chk in chunk_res:
                ret += chk

        ret.sort(key=lambda entry: entry["priority"])

        return ret
