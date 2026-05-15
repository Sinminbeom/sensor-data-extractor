from typing import Any, Iterable, List, Tuple

from python_library.category.app_category import AppCategory
from python_library.category.category_action import CategoryAction
from python_library.category.category_group import CategoryGroup

from config.project_config import ProjectConfig
from process_category.enum_category import E_CATE, E_CATE_META_ELE
# replayer 패턴을 적용해 CategoryGroup 트리로 등록하고, worker N개도 register 시점에 펼친다.
class ProcessCategory(AppCategory):
    def __init__(self) -> None:
        super().__init__()

    def register_category(self) -> None:
        self.cate_reg_queue[E_CATE.EXTRACTOR] = lambda: self.register_extractor()
        self.cate_reg_queue[E_CATE.WEB_SERVICE] = lambda: self.register_web_service()

    def register_extractor(self) -> None:
        extractor = CategoryGroup()
        common = CategoryGroup()
        worker = CategoryGroup()

        # Manager 1개
        common.push(
            E_CATE.E_EXTRACTOR.E_COMMON.E_EXTRACTOR_MANAGER[E_CATE_META_ELE.NAME],
            CategoryAction(E_CATE.E_EXTRACTOR.E_COMMON.E_EXTRACTOR_MANAGER[E_CATE_META_ELE.LAMBDA]),
        )

        # Worker N개 — PROCESS_COUNT 에서 manager 1개를 뺀 수
        worker_count = max(0, ProjectConfig.instance().process_count - 1)
        worker_factory_lambda = E_CATE.E_EXTRACTOR.E_WORKER.E_EXTRACTOR_WORKER[E_CATE_META_ELE.LAMBDA]
        for idx in range(worker_count):
            worker_name = f"EXTRACTOR_WORKER_{idx}"
            worker.push(worker_name, CategoryAction(worker_factory_lambda))

        extractor.push(E_CATE.E_EXTRACTOR.COMMON, common)
        extractor.push(E_CATE.E_EXTRACTOR.WORKER, worker)
        self.cate_queue[E_CATE.EXTRACTOR] = extractor

    def register_web_service(self) -> None:
        web_service = CategoryGroup()
        common = CategoryGroup()

        common.push(
            E_CATE.E_WEB_SERVICE.E_COMMON.E_WEB_SERVICE[E_CATE_META_ELE.NAME],
            CategoryAction(E_CATE.E_WEB_SERVICE.E_COMMON.E_WEB_SERVICE[E_CATE_META_ELE.LAMBDA]),
        )

        web_service.push(E_CATE.E_WEB_SERVICE.COMMON, common)
        self.cate_queue[E_CATE.WEB_SERVICE] = web_service

    def get_process_list_category(self, *_cate) -> List[Tuple[Any, Any]]:
        """legacy GetProcessListsCate 와 동일한 역할.
        depth=1/2/3 모두 지원하며 leaf (cate_name, CategoryAction) tuple list로 반환.
        """
        def _items(group: Any) -> Iterable[Tuple[Any, Any]]:
            if group is None:
                return []
            if hasattr(group, "items") and callable(group.items):
                return group.items()
            if hasattr(group, "queue"):
                return group.queue.items()
            if hasattr(group, "_queue"):
                return group._queue.items()
            if isinstance(group, dict):
                return group.items()
            raise TypeError(f"Unsupported group type: {type(group)}")

        def _get(group: Any, key: Any) -> Any:
            if group is None:
                return None
            if hasattr(group, "get") and callable(group.get):
                return group.get(key)
            if hasattr(group, "queue"):
                return group.queue.get(key)
            if hasattr(group, "_queue"):
                return group._queue.get(key)
            if isinstance(group, dict):
                return group.get(key)
            return None

        if len(_cate) not in (1, 2, 3):
            raise ValueError("get_process_list_category expects 1~3 category keys")

        cate1 = _cate[0]
        cate1_group = self.cate_queue.get(cate1)
        if cate1_group is None:
            return []

        if len(_cate) == 1:
            ret: List[Tuple[Any, Any]] = []
            for _, cate2_group in _items(cate1_group):
                for k, v in _items(cate2_group):
                    ret.append((k, v))
            return ret

        cate2 = _cate[1]
        cate2_group = _get(cate1_group, cate2)
        if cate2_group is None:
            return []

        if len(_cate) == 2:
            return [(k, v) for k, v in _items(cate2_group)]

        cate3 = _cate[2]
        leaf = _get(cate2_group, cate3)
        if leaf is None:
            return []
        return [(cate3, leaf)]
