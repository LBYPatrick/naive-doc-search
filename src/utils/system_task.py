from asyncio import StreamReader
from asyncio.subprocess import Process
from typing import Optional, List, Dict
import asyncio

from src.utils.util import Util


class SystemTask:
    cmd: Optional[str] = None
    outputs: Dict[str, List[str]] = None
    proc: Process = None
    __io_tasks: Dict[str, asyncio.Task] = None

    def __init__(self, cmd: str):
        self.cmd = cmd
        self.__io_tasks = {}
        self.outputs = {}

    async def __read_output(self, name: str, stream: StreamReader):
        write_mutex = asyncio.Lock()

        while True:
            try:
                if stream.at_eof():
                    break

                content = (await stream.readline()).decode()

                await write_mutex.acquire()
                if name not in self.outputs:
                    self.outputs[name] = []

                self.outputs[name].append(content)
                write_mutex.release()

            except Exception as e:
                Util.warn(e, require_stack=True)
                break

    def is_alive(self):
        return self.proc is not None and self.proc.returncode is None

    def return_code(self) -> int:
        return None if self.is_alive() else self.proc.returncode

    async def start(self):
        self.proc = await asyncio.create_subprocess_shell(
            self.cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        io_task_mp = {"stdout": self.proc.stdout, "stderr": self.proc.stderr}

        self.__io_tasks = {
            name: asyncio.create_task(self.__read_output(name, stream))
            for name, stream in io_task_mp.items()
        }
