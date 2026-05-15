from __future__ import annotations

from python_library.logger.app_logger import AppLogger
from python_library.process.queue_process import QueueProcess

from config.project_config import ProjectConfig
# 베이스로 두고 logger/config init 책임을 _set_config에 모아둠. 동일 패턴 채택.
class AppProcess(QueueProcess[str]):
    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(process_name)
        self._app_name = app_name

    def _set_config(self) -> None:
        AppLogger.set_config(
            ProjectConfig.DEFAULT_LOGGING_CONFIG_PATH,
            f"{ProjectConfig.LOGGER_BASE_NAME}.{self.name}",
        )
        ProjectConfig.set_config(ProjectConfig.DEFAULT_CONFIG_PATH)

    def get_app_name(self) -> str:
        return self._app_name
