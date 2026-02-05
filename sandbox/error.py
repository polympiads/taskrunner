
class IsolateError (RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)

class SandboxDoubleFree (RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)
class SandboxUseAfterFree (RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)
