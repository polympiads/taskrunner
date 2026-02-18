
from typing import List, Tuple

from django.conf import settings

class Isolate:
    MAX_NUMBER_PROCESS = -1

    @staticmethod
    def base_command (box_id: int):
        if settings.USE_CGROUPS:
            return [ "isolate", f"--box-id={box_id}", "--cg" ]
        return [ "isolate", f"--box-id={box_id}" ]

    @staticmethod
    def init_command (box_id: int):
        return [ *Isolate.base_command(box_id), "--init" ]
    @staticmethod
    def cleanup_command (box_id: int):
        return [ *Isolate.base_command(box_id), "--cleanup" ]

    @staticmethod
    def run_command (
                box_id: int,

                command: List[str],
                meta_file: str | None,
            
                time       : "float | None",
                wall_time  : "float | None",
                extra_time : "float | None",

                memory : "int | None", 

                stdin:  "str | None",
                stdout: "str | None",
                stderr: "str | None",
                
                num_process : "int | None",
                env_vars : "List[Tuple[str, str]]",
                directories : "List[str | Tuple[str, str]]",

                enable_simple_memory : bool,
                enable_cgroup_memory : bool
            ):
        result = Isolate.base_command(box_id)
        result.append("--run")

        if meta_file is not None: result.append(f"--meta={meta_file}")

        if time       is not None: result.append(f"--time={time}")
        if wall_time  is not None: result.append(f"--wall-time={wall_time}")
        if extra_time is not None: result.append(f"--extra-time={extra_time}")

        if memory is not None:
            if settings.USE_CGROUPS and enable_cgroup_memory:
                result.append(f"--cg-mem={memory}")
            if (not settings.USE_CGROUPS) and enable_simple_memory:
                result.append(f"--mem={memory}")

        if stdin  is not None: result.append(f"--stdin={stdin}")
        if stdout is not None: result.append(f"--stdout={stdout}")
        if stderr is not None: result.append(f"--stderr={stderr}")

        if num_process is not None:
            if num_process == Isolate.MAX_NUMBER_PROCESS:
                result.append("--processes")
            else:
                result.append(f"--processes={num_process}")
        
        for directory in directories:
            if isinstance(directory, tuple):
                inbox, outbox = directory
                result.append(f"--dir={inbox}={outbox}")
            else:
                result.append(f"--dir={directory}")
        
        for key, value in env_vars:
            result.append(f"--env={key}={value}")

        result.append("--")
        result.extend(command)

        return result
