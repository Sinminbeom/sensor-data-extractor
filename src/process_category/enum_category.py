from python_library.define.enum import IENUM

from app.extractor.process.manager.manager import ExtractorManager
from app.extractor.process.worker.worker import ExtractorWorker
from app.web_service.process.web_service_process import WebServiceProcess

class E_CATE_META_ELE(IENUM):
    NAME = 0
    LAMBDA = 1
# replayer 스타일로 EXTRACTOR (manager+worker N개) / WEB_SERVICE 2개 카테고리로 분리해
# process_category로 등록하도록 변경.
class E_CATE(IENUM):
    EXTRACTOR = "EXTRACTOR"
    WEB_SERVICE = "WEB_SERVICE"

    class E_EXTRACTOR(IENUM):
        COMMON = "COMMON"
        WORKER = "WORKER"

        class E_COMMON(IENUM):
            EXTRACTOR_MANAGER = "EXTRACTOR_MANAGER"
            E_EXTRACTOR_MANAGER = (
                EXTRACTOR_MANAGER,
                lambda _app_name, _process_name: ExtractorManager(_app_name, _process_name),
            )

        class E_WORKER(IENUM):
            EXTRACTOR_WORKER = "EXTRACTOR_WORKER"
            E_EXTRACTOR_WORKER = (
                EXTRACTOR_WORKER,
                lambda _app_name, _process_name: ExtractorWorker(_app_name, _process_name),
            )

    class E_WEB_SERVICE(IENUM):
        COMMON = "COMMON"

        class E_COMMON(IENUM):
            WEB_SERVICE = "WEB_SERVICE"
            E_WEB_SERVICE = (
                WEB_SERVICE,
                lambda _app_name, _process_name: WebServiceProcess(_app_name, _process_name),
            )
