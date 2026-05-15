from __future__ import annotations

from python_library.define.enum import IENUM
from python_library.storage.local.local_storage_factory import LocalStorageFactory
from python_library.storage.local.local_storage_info_factory import LocalStorageInfoFactory
from python_library.storage.storage import IStorage

from config.project_config import ProjectConfig

# storage 종류 enum — application.conf의 SRC_STORAGE.TYPE / DST_STORAGE.TYPE 값과 매칭.
class E_STORAGE_TYPE(IENUM):
    LOCAL = "LOCAL"
    # GOOGLE_DRIVE = "GOOGLE_DRIVE"  # python-library 측 구현 추가 후 활성화 예정

class StorageBuilder:
    """ProjectConfig의 SRC_STORAGE / DST_STORAGE 카테고리를 읽어 python-library IStorage 인스턴스를 만든다.

    추후 Google Drive 등 추가 시 _build()의 분기만 늘리면 된다.
    """

    @staticmethod
    def build_source() -> tuple[IStorage, str]:
        # 본 구현은 (storage, root_path) tuple로 반환 — 호출 측이 root_path를 prefix로 결합.
        cfg = ProjectConfig.instance()
        return StorageBuilder._build(cfg.src_storage_type), cfg.src_storage_root

    @staticmethod
    def build_destination() -> tuple[IStorage, str]:
        cfg = ProjectConfig.instance()
        return StorageBuilder._build(cfg.dst_storage_type), cfg.dst_storage_root

    @staticmethod
    def _build(storage_type: str) -> IStorage:
        upper = storage_type.upper()
        if upper == E_STORAGE_TYPE.LOCAL:
            storage = LocalStorageFactory(LocalStorageInfoFactory()).create_storage()
            storage.connect()
            return storage
        raise ValueError(f"Unsupported storage type: {storage_type}")
