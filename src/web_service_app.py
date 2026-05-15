import time

from app.app_object import MultiProcessManagerAppFromCate
from config.project_config import ProjectConfig
from process_category.enum_category import E_CATE
from process_category.process_category import ProcessCategory
# Flask 단독 실행 대신 process 카테고리(WEB_SERVICE)로 등록해 ProcessManager가 lifecycle을 관리하도록 통일.
class WebServiceApp(MultiProcessManagerAppFromCate):
    def __init__(self, *_cate) -> None:
        super().__init__(E_CATE.WEB_SERVICE, *_cate)

    def init(self) -> None:
        self.get_multi_process_manager().start()

    def on_run(self) -> None:
        time.sleep(0.005)

def main() -> None:
    ProjectConfig.set_config(ProjectConfig.DEFAULT_CONFIG_PATH)
    ProcessCategory.instance().register_web_service()

    app = WebServiceApp(E_CATE.WEB_SERVICE)
    app.init()
    app.run()

if __name__ == "__main__":
    main()
