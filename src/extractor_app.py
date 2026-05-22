"""sensor-data-extractor extractor 진입점 — manager 1 + module N 등록."""

from python_library.process.multi_process_manager import MultiProcessManager

from app.extractor.process.manager.manager import ExtractorManager
from app.extractor.process.module.module import ExtractorModule
from config.project_config import ProjectConfig
from define.process_name import EXTRACTOR_MANAGER, EXTRACTOR_MODULE_PREFIX


def main() -> None:
    ProjectConfig.set_config(ProjectConfig.DEFAULT_CONFIG_PATH)
    cfg = ProjectConfig.instance()

    mpm = MultiProcessManager()
    mpm.append(ExtractorManager("extractor", EXTRACTOR_MANAGER))

    module_count = max(0, cfg.process_count - 1)
    for idx in range(module_count):
        mpm.append(ExtractorModule("extractor", f"{EXTRACTOR_MODULE_PREFIX}{idx}"))

    mpm.run()


if __name__ == "__main__":
    main()
