from starlette.requests import Request
from starlette.responses import JSONResponse

from src.utils.util import Util


class WebUtil:

    @staticmethod
    def make_response(content: any, is_good: bool = True, status_code: int = 200):
        return JSONResponse(
            {
                "status": 0 if is_good else 1,
                "timestamp": Util.time_now().isoformat(),
                "content": content,
            },
            status_code=status_code,
        )

    @staticmethod
    def make_success(content: any, status_code: int = 200):
        return WebUtil.make_response(
            content=content, is_good=True, status_code=status_code
        )

    @staticmethod
    def make_error(error: any, status_code: int = 403):
        return WebUtil.make_response(
            Util.get_proper_msg(error), is_good=False, status_code=status_code
        )

    @staticmethod
    async def get_params(request: Request):
        is_post = request.method == "POST"

        if is_post:
            return await request.json()
        else:
            return dict(request.query_params)

    @staticmethod
    def ensure_valid_request(params: dict[str, any], *required_args):
        missing_args = [
            arg
            for arg in required_args
            if arg not in params.keys() or params[arg] is None
        ]

        if len(missing_args) > 0:
            raise Exception(f"required args missing: {missing_args}")
