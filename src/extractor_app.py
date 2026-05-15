import time

from app.app_object import MultiProcessManagerAppFromCate
from config.project_config import ProjectConfig
from process_category.enum_category import E_CATE
from process_category.process_category import ProcessCategory
# replayer 패턴을 따라 ProcessCategory가 worker 등록을 담당하고 app은 단순히 MultiProcessManagerAppFromCate를 상속.
class ExtractorApp(MultiProcessManagerAppFromCate):
    def __init__(self, *_cate) -> None:
        super().__init__(E_CATE.EXTRACTOR, *_cate)

    def init(self) -> None:
        self.get_multi_process_manager().start()

    def on_run(self) -> None:
        time.sleep(0.005)

def main() -> None:
    ProjectConfig.set_config(ProjectConfig.DEFAULT_CONFIG_PATH)
    ProcessCategory.instance().register_extractor()

    app = ExtractorApp(E_CATE.EXTRACTOR)
    app.init()
    app.run()

if __name__ == "__main__":
    main()
