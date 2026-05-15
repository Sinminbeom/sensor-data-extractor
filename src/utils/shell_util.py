import subprocess
from typing import Tuple
# 외부 shell 명령 실행 wrapper. AT128 / RSBP 추출기가 tar 생성에 사용.
class ShellUtil:
    def __init__(self, command: str, use_shell: bool = True) -> None:
        self._command = command
        self._shell = use_shell

    def run(self) -> Tuple[str, str]:
        proc = subprocess.run(
            self._command,
            shell=self._shell,
            capture_output=True,
            text=True,
        )
        return proc.stdout, proc.stderr
