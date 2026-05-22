"""sensor-data-extractor web service 진입점 — FastAPI process 1 개 등록."""

from python_library.process.multi_process_manager import MultiProcessManager

from app.web_service.process.web_service_process import WebServiceProcess
from config.project_config import ProjectConfig
from define.process_name import WEB_SERVICE


def main() -> None:
    ProjectConfig.set_config(ProjectConfig.DEFAULT_CONFIG_PATH)

    mpm = MultiProcessManager()
    mpm.append(WebServiceProcess("web_service", WEB_SERVICE))
    mpm.run()


if __name__ == "__main__":
    main()
