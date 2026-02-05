
class Isolate:
    @staticmethod
    def base_command (box_id: int):
        return [ "isolate", f"--box-id={box_id}" ]

    @staticmethod
    def init_command (box_id: int):
        return [ *Isolate.base_command(box_id), "--init" ]
    @staticmethod
    def cleanup_command (box_id: int):
        return [ *Isolate.base_command(box_id), "--cleanup" ]
