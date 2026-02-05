
from sandbox.error import IsolateError
from sandbox.isolate import Isolate
from sandbox.manager import SandboxManager
from sandbox.subprocess import run_subprocess_command

from .telemetry import start_as_current_span, trace, sandbox_logger
from .manager   import SandboxManager

class Sandbox:
    def __init__ (self, box_id: int, box_dir: str):
        self.box_id  = box_id
        self.box_dir = box_dir

    @staticmethod
    async def create_sandbox () -> "Sandbox":
        with start_as_current_span("sandbox.create") as span:
            manager : SandboxManager = SandboxManager.instance()
            box_id  : int = await manager.allocate_id()

            trace.get_current_span() \
                .add_event( f"Acquired box id {box_id}" )

            try:
                proc, stdout, stderr = await run_subprocess_command(
                    *Isolate.init_command( box_id ) )

                if proc.returncode != 0:
                    raise IsolateError( f"Could not create box with id {box_id}" )
                
                box_dir = stdout.decode().strip()

                trace.get_current_span().set_status(trace.StatusCode.OK)
                sandbox_logger.info(
                    "Successfully created sandbox with id %s (%s)",
                    box_id, box_dir )
                
                return Sandbox( 
                    box_id, 
                    box_dir
                )
            except Exception as err:
                trace.get_current_span().set_status(trace.StatusCode.ERROR)
                sandbox_logger.critical(
                    "Could not create sandbox with id %s",
                    box_id )

                await manager.free_id(box_id)      
                raise err
            
    async def free_sandbox (self):
        with start_as_current_span("sandbox.free") as span:
            await run_subprocess_command( *Isolate.cleanup_command(self.box_id) )
            
            manager : SandboxManager = SandboxManager.instance()
            await manager.free_id(self.box_id)
