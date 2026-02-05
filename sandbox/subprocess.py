
from typing import List
from opentelemetry import trace

import asyncio

def isolate_base_cmd (box_id: int):
    return [ "isolate", f"--box-id={box_id}" ]

async def run_subprocess_command (*cmd: List[str]):
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
    except Exception as exc:
        trace.get_current_span().add_event(
            f"Failed to run command {cmd}"
        )
        raise exc

    stdout, stderr = await proc.communicate()

    trace.get_current_span().add_event(
        f"Successfully ran command {cmd} (retcode={proc.returncode})",
        attributes={
            "stdout": stdout,
            "stderr": stderr
        })
    
    return (proc, stdout, stderr)
