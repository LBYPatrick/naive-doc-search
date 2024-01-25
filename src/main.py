# This is a sample Python script.
import asyncio

from src.utils.system_task import SystemTask


# Press ⌥⇧R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f"Hi, {name}")  # Press ⌃' to toggle the breakpoint.


async def main():
    t = SystemTask("ls")

    await t.start()

    while t.is_alive():
        await asyncio.sleep(0)


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    print_hi("PyCharm")

    asyncio.run(main())


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
