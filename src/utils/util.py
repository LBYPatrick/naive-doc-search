import asyncio
import copy
import datetime
import functools
import json
import logging
import math
import os.path
import pathlib
import pickle
import shutil
import sys
import traceback
import re
import uuid
from asyncio import AbstractEventLoop
from enum import Enum
from functools import total_ordering
from typing import Optional, Any, Coroutine, Union, Dict, List

import json5
import multiexit
import numpy
import pandas
import nest_asyncio
from dotenv import load_dotenv


@total_ordering
class LogLevel(Enum):
    RELEASE = 1
    VERBOSE = 2
    DEBUG = 3

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value


class Util:
    is_env_loaded = False
    is_initialized = False
    log_level = LogLevel.DEBUG
    env_vals = {}
    io_loop = None
    config = None

    @classmethod
    def init(cls):
        if not cls.is_initialized:
            Util.get_env_param("")
            nest_asyncio.apply()

        cls.is_initialized = True

    @staticmethod
    def update_log_level(new_level: LogLevel):
        Util.log_level = new_level

    @staticmethod
    def ensure_required_rule_params(params: dict, *args):
        missing = []

        for key in args:
            if key not in params or params[key] is None:
                missing.append(key)

        if len(missing) > 0:
            raise Exception(
                f"missing keys in rules params for {params['function']}: {','.join(missing)}"
            )

    @staticmethod
    def get_percentile(sorted_data_arr: list, data_pt):
        return (
            numpy.searchsorted(sorted_data_arr, data_pt) * 100.0 / len(sorted_data_arr)
        )

    @staticmethod
    def get_file_paths(
        result_paths_buffer: list, base_path: str, csv_only: bool = True
    ) -> None:
        """
        Iteratively find all paths that lives underneath current directory
        """
        if not pathlib.Path(base_path).exists():
            return
        elif pathlib.Path(base_path).is_file():
            result_paths_buffer.append(base_path)
            return

        dirs = [
            directory
            for directory in pathlib.Path(base_path).iterdir()
            if pathlib.Path(base_path).is_dir()
        ]

        files = [
            str(file)
            for file in pathlib.Path(base_path).iterdir()
            if file.is_file()
            and not file.name.startswith(".")  # No hidden files
            and (not csv_only or file.name.endswith(".csv"))  # CSV only mode
        ]

        dirs = [
            directory
            for directory in dirs
            if not directory.name.startswith(".")  # no hidden directories
            and not directory.name.startswith("__")  # Skip python cache folder
        ]

        for directory in dirs:
            Util.get_file_paths(result_paths_buffer, str(directory))

    @staticmethod
    @functools.lru_cache
    def get_abs_path(relative_path: str, auto_create_path=False):
        """
        Get absolute path with a path relative to the working directory
        """

        ret = os.path.join(os.getcwd(), relative_path)

        # automatically create path if ENOENT
        if auto_create_path:
            dir_name = ret

            if not pathlib.Path(dir_name).is_dir():
                dir_name = pathlib.Path(dir_name).parent.resolve()

            pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)

        return ret

    @staticmethod
    @functools.lru_cache
    def enable_multiexit():
        multiexit.install()
        return True

    @staticmethod
    @functools.lru_cache
    def read_csv(file_path: str, encoding="utf-8"):
        return pandas.read_csv(file_path, encoding=encoding)

    @staticmethod
    @functools.lru_cache
    def read_excel(file_path: str, sheet_name=None, data_type=None):
        return pandas.read_excel(file_path, sheet_name=sheet_name, dtype=data_type)

    @staticmethod
    def read_txt(file_path, encoding="utf-8"):
        """
        Reads a txt file
        Args:
            file_path: file path
            encoding: file encoding, defaults to utf-8
        Returns:
            list[str]:A cleaned up list of lines, but \n and \t  will be stripped
        """
        file = open(file_path, "r", encoding=encoding)
        return [line.strip() for line in file if (line is not None and len(line) > 0)]

    @staticmethod
    @functools.lru_cache
    def read_json(file_path, encoding="utf-8-sig") -> Union[Dict, List[Dict], None]:
        """
        Reads a JSON with Comments file

        Args:
            file_path: python
            encoding: file encoding, defaults to utf-8-sig
        Returns:
            A dict without comments
        """

        content = open(file_path, "r", encoding=encoding).read()

        return json5.loads(content.strip())

    @staticmethod
    def time_now():
        return datetime.datetime.now()

    @staticmethod
    def get_elapsed_time_ms(start_time):
        now = Util.time_now()

        if not isinstance(start_time, datetime.datetime):
            start_time = Util.time_now()

        diff = now - start_time

        return float(diff.total_seconds()) * 1000.0

    @staticmethod
    def get_elapsed_time_ms_str(start_time):
        return "{0:0.2f} ms".format(Util.get_elapsed_time_ms(start_time))

    @staticmethod
    def get_elapsed_time_seconds_str(start_time):
        now = Util.time_now()

        if not isinstance(start_time, datetime.datetime):
            start_time = Util.time_now()

        diff = now - start_time

        return "{0:0.2f} s".format(float(diff.total_seconds()))

    @classmethod
    def read_map_value(cls, mp: dict, key: str, default_value=None):
        if key not in mp or mp[key] is None:
            Util.warn(f"no key {key} in {mp}")
            return default_value

        return mp[key]

    @staticmethod
    def shrink_dict(raw_dict: dict):
        keys = raw_dict.keys()
        mask = {key: True for key in keys}

        for key in mask.keys():
            if raw_dict[key] is None:
                mask[key] = False

            try:
                if len(raw_dict[key]) == 0:
                    mask[key] = False
            except Exception as e:
                pass

        valid_keys = [key for key in mask.keys() if mask[key]]
        return Util.copy_dict(raw_dict, valid_keys)

    @staticmethod
    def copy_dict(mp: dict, include_keys: list[str] = None):
        dummy = copy.deepcopy(mp)
        ret = {}

        if include_keys is None:
            return dummy

        for key in include_keys:
            if key in mp:
                ret[key] = dummy[key]

        return ret

    @classmethod
    def print_msg(cls, tag, msg, require_stack=False, tail="\n", is_stderr=False):
        app_name = cls.get_env_param("app_name", "naive_doc_search")

        msg = Util.get_proper_msg(msg)
        time = datetime.datetime.now().isoformat()

        payload = f"{time}\t\t[{app_name}][{tag}] {msg}"
        print(
            payload, end=tail, file=sys.stderr if is_stderr else sys.stdout, flush=True
        )

        if require_stack:
            traceback.print_exc()
        #
        sys.stdout.flush()
        sys.stderr.flush()

        return payload

    @staticmethod
    def mute():
        sys.stdout = open(os.devnull, "w")

    @staticmethod
    def unmute():
        sys.stdout = sys.__stdout__

    @staticmethod
    def info(message, require_stack=False, tail="\n"):
        return Util.print_msg("INFO", message, require_stack, tail)

    @staticmethod
    def debug(message, require_stack=False, tail="\n"):
        if Util.log_level < LogLevel.DEBUG:
            return

        return Util.print_msg("DEBUG", message, require_stack, tail)

    @staticmethod
    def get_proper_msg(msg):
        """
        Args:
            msg:

        Returns:

        """
        return (
            msg
            if not isinstance(msg, Exception)
            else "[EXCEPTION]{}: {}".format(msg.__class__, msg.args)
        )

    @staticmethod
    def error(message, require_stack=True, tail="\n"):
        if Util.log_level < LogLevel.VERBOSE:
            return

        return Util.print_msg("ERROR", message, require_stack, tail, True)

    @staticmethod
    def divider(length=50):
        Util.verbose("=" * length)

    @staticmethod
    def verbose(message, require_stack=False, tail="\n"):
        if Util.log_level < LogLevel.VERBOSE:
            return

        return Util.print_msg("VERBOSE", message, require_stack, tail)

    @staticmethod
    def warn(message, require_stack=False, tail="\n"):
        if Util.log_level < LogLevel.VERBOSE:
            return

        return Util.print_msg("WARN", message, require_stack, tail, is_stderr=True)

    @staticmethod
    def get_env_params(*args):
        ret = []
        for key in args:
            ret.append(Util.get_env_param(key, None, throw_exception=True))

        return tuple(ret)

    @staticmethod
    def init_dotenv():
        if not Util.is_env_loaded:
            load_dotenv()
            Util.is_env_loaded = True

    @staticmethod
    def str_to_bool(bool_str: str):
        if isinstance(bool_str, bool):
            return bool_str

        yes = ["yes", "true", "1", "on", "enabled"]
        if bool_str.lower() in yes:
            return True
        else:
            return False

    @staticmethod
    def set_env_param(key: str, value):
        Util.init_dotenv()

        os.environ[key.upper()] = str(value)

    @staticmethod
    def get_env_param(
        key: str, default_value=None, cast_type=None, throw_exception=False
    ):
        try:
            Util.init_dotenv()
            result = os.environ.get(str(key).upper())

            ret = default_value if result is None else result

            if cast_type is not None and ret is not None:
                ret = Util.str_to_bool(ret) if cast_type is bool else cast_type(ret)

            if ret is not None:
                Util.env_vals[str(key).lower()] = ret

            return ret

        except Exception as e:
            Util.error(f"env key cannot be read: {key}", False)
            Util.error(e)

            Util.env_vals[str(key).lower()] = default_value

            if throw_exception:
                raise e
            else:
                return default_value

    @staticmethod
    def get_uid(version=4):
        funcs = {1: uuid.uuid1, 3: uuid.uuid3, 4: uuid.uuid4, 5: uuid.uuid5}

        if version not in funcs.keys():
            return str(funcs[4]())
        else:
            return str(funcs[version]())

    @staticmethod
    def mute_logger():
        logging.disable(logging.INFO)
        logging.disable(logging.DEBUG)
        logging.disable(logging.CRITICAL)
        logging.disable(logging.FATAL)
        logging.disable(logging.ERROR)

    @staticmethod
    def mute_all():
        Util.mute_logger()
        Util.mute()

    @staticmethod
    def write_pkl(obj: object, path: Optional[str] = None, throw_exception=True):
        try:
            if obj is None:
                return

            if path is None:
                path = Util.get_abs_path(f"pkl/{Util.get_uid()}.pkl", True)

            tmp_path = path + "." + re.sub("-", "", Util.get_uid()[:10])

            file = open(tmp_path, "wb")
            pickle.dump(obj, file)
            file.close()

            if os.path.isfile(path):
                os.remove(path)

            shutil.move(tmp_path, path)

            return path

        except Exception as e:
            Util.warn(e)
            if throw_exception:
                raise e
            else:
                return None

    @staticmethod
    def print_variable(name: str, value: Any):
        length = "N/A"

        if hasattr(value, "__len__"):
            length = str(len(value))

        Util.debug(
            f"VARIABLE: {name}, \n\ttype: {type(value)}\n\tvalue: {str(value)}\n\n\t Length: {length}"
        )

    @staticmethod
    def read_pkl(path: str, default_value=None, throw_exception=True):
        try:
            # Check if file exists
            probe = open(path, "rb")

            probe.read()
            probe.close()
            # with open(path, "rb") as f:
            #     f.read()
            #

            file = open(path, "rb")

            ret = pickle.load(file)
            file.close()

            if ret is None:
                raise Exception(f"Bad value from pickle file: {path}, value: {ret}")

            return ret

        except Exception as e:
            Util.error(e)
            if throw_exception:
                raise e
            else:
                return default_value

    @staticmethod
    def json_to_string(obj) -> str:
        try:
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except Exception as e:
            Util.warn(f"Cannot resolve JSON object: {obj}", False)
            Util.warn(e)
            return str(obj)

    @staticmethod
    def func_hash(*args, **kwargs):
        mp = {}
        anon = []

        for arg in args:
            hashed = Util.get_uid()

            if arg is bool:
                anon.append("True" if arg else "False")
                continue

            try:
                hashed = str(arg)
            except Exception as e:
                Util.error(e)
            finally:
                anon.append(hashed)

        mp = {"anon": anon, **kwargs}
        ret = json.dumps(mp)

        return ret

    @classmethod
    async def run_async_with_sleep(cls, task: Coroutine):
        ret = await task
        await asyncio.sleep(0)
        return ret

    @classmethod
    def run_async_as_blocking(cls, task: Coroutine):
        cls.init()

        loop: Optional[AbstractEventLoop] = None

        try:
            loop = asyncio.get_running_loop()
        except Exception as e:
            Util.warn(e)

            if Util.io_loop is None:
                Util.io_loop = asyncio.new_event_loop()

            loop = Util.io_loop

        return loop.run_until_complete(cls.run_async_with_sleep(task))

    @classmethod
    async def sync_to_async(cls, func):
        cls.init()
        return await asyncio.get_running_loop().run_in_executor(None, func)

    @staticmethod
    def ensure_valid_dict(params: dict[str, any], *required_args):
        missing_args = [
            arg
            for arg in required_args
            if arg not in params.keys() or params[arg] is None
        ]

        if len(missing_args) > 0:
            raise Exception(f"required key missing: {missing_args}")

    @staticmethod
    def get_folder_size(folder_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)
        return total_size
