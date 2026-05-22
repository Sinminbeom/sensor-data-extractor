from python_library.logger.app_logger import AppLogger

from common.process.app_process import AppProcess
from config.project_config import ProjectConfig
# MultiProcessManager 에 등록 가능한 AppProcess wrapper.
# FastAPI app 자체 코드는 app/web_service/server.py로 분리 (uvicorn 으로 실행).
class WebServiceProcess(AppProcess):
    def __init__(self, app_name: str, process_name: str) -> None:
        super().__init__(app_name, process_name)

    def action(self) -> None:
        try:
            self._set_config()
            AppLogger.instance().info(f"[{self.name}] WebServiceProcess start")

            # 지연 import — child process boundary에서 FastAPI app 초기화
            from app.web_service.server import WebServiceServer

            cfg = ProjectConfig.instance()
            server = WebServiceServer()
            server.run(host=cfg.bind_ip, port=cfg.bind_port)

        except Exception as e:
            AppLogger.instance().exception(e)
            raise
