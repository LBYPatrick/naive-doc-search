from typing import Any, Dict

from src.utils.util import Util


class Config:
    data = None

    @classmethod
    def get_config_param(
        cls,
        key,
        default_value: Any = None,
        throw_exception: bool = False,
        config_path: str = None,
    ) -> Any:
        try:
            if cls.data is None:
                if config_path is None:
                    config_path = Util.get_abs_path("config.json")

                cls.data = Util.read_json(config_path)

            if key not in cls.data:
                raise Exception(f"missing key: {key}")

            return cls.data[key]

        except Exception as e:
            Util.error(e)

            if throw_exception:
                raise e
            else:
                return default_value

    @classmethod
    def get_child_param(cls, parent, child, default_value: Any = None):
        conf = cls.get_config_param(parent, {})

        return Util.read_map_value(conf, child, default_value)
