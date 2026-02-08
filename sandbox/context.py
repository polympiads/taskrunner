
from sandbox.sandbox import Sandbox


class sandbox_open ():
    sandbox: "Sandbox | None"

    def __init__(self, sandbox = None):
        self.sandbox = sandbox

    async def __aenter__ (self):
        if self.sandbox is None:
            self.sandbox = await Sandbox.create_sandbox()
        return self.sandbox
    async def __aexit__ (self, exc_type, exc_val, exc_tb):
        await self.sandbox.free_sandbox(True)
