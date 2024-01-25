import functools
import re

from utils.util import Util


class StringUtil:
    @staticmethod
    def float_to_str(number: float):
        return "{0:0.2f}".format(number)

    @staticmethod
    @functools.lru_cache(maxsize=114514)
    def get_cleaned_question(question):
        punc = [
            # "，",
            # ",",
            # "。",
            # ".",
            # "？",
            # "?",
            # "!",
            # "！",
            # "“", "”", "\"", '\'', '’', '‘', '(', ")", '（', "）", "：", "；", ":", ";", '{', "}", '「', "」",  # 全角和半角的分隔符
            "\n",
            "\t",
            "\r",
        ]
        new_text = [w for w in question if w not in punc]
        question_cleaned = "".join(new_text)

        puncs_to_fix = {
            "：": ":",
            "；": ";",
            "“": '"',
            "”": '"',
            "（": "(",
            "）": ")",
            "「": "{",
            "」": "}",
        }

        for key, value in puncs_to_fix.items():
            question_cleaned = re.sub(key, value, question_cleaned)

        return question_cleaned

    @staticmethod
    def convert_to_full_width_char(unicode_str: str, reverse=False):
        """ """
        if len(unicode_str) > 1:
            return unicode_str
        if (
            unicode_str.isalnum()
            or unicode_str == "."
            or unicode_str == "%"
            or unicode_str == "-"
        ):
            return unicode_str

        inside_code = ord(unicode_str)

        # 半角转全角
        if not reverse:
            if inside_code < 0x0020 or inside_code > 0x7E:
                return unicode_str
            if inside_code == 0x0020:
                inside_code = 0x3000
            else:
                inside_code += 0xFEE0
        # 全角转半角
        else:
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xFEE0
            if inside_code < 0x0020 or inside_code > 0x7E:
                return unicode_str

        return chr(inside_code)

    @staticmethod
    @functools.lru_cache(16384)
    def get_jaccard_similarity(left_str: str = None, right_str: str = None):
        left_str = set(left_str)
        right_str = set(right_str)

        return len(left_str & right_str) / len(left_str | right_str)

    @staticmethod
    @functools.lru_cache
    def wash_str_wo_chn_puncs(old_str: str):
        puncs_to_fix = {
            "：": ":",
            "；": ";",
            "“": '"',
            "”": '"',
            "（": "(",
            "）": ")",
            "「": "{",
            "」": "}",
        }
        old_str = str(old_str)

        for key, value in puncs_to_fix.items():
            old_str = re.sub(key, value, old_str)

        return old_str

    @staticmethod
    @functools.lru_cache
    def is_chinese(uchar):
        return True if "\u4e00" <= uchar <= "\u9fa5" else False

    @staticmethod
    @functools.lru_cache
    def reserve_chinese_chars(content):
        return "".join([char for char in content if Util.is_chinese(char)])
