from __future__ import annotations

from config.project_config import ProjectConfig
# Redis 접속 정보 + 두 큐 (COM_QUEUE / JOB_LIST_QUEUE) 이름 + test mode suffix 헬퍼.
# 본 구현은 ProjectConfig.REDIS 카테고리 키만 추출하는 thin layer — connection / queue 동작은 분리된 곳에서.
class RedisConfig:
    def __init__(self, project_config: ProjectConfig | None = None) -> None:
        cfg = project_config or ProjectConfig.instance()
        self._cfg = cfg
        self.ip: str = cfg.get_config(
            ProjectConfig.E_CATE_TYPE.REDIS, ProjectConfig.E_CATE_ELE_REDIS.IP
        )
        self.port: int = int(
            cfg.get_config(ProjectConfig.E_CATE_TYPE.REDIS, ProjectConfig.E_CATE_ELE_REDIS.PORT)
        )
        self.com_queue_name: str = cfg.get_config(
            ProjectConfig.E_CATE_TYPE.REDIS, ProjectConfig.E_CATE_ELE_REDIS.COM_QUEUE_NAME
        )
        self.job_list_queue_name: str = cfg.get_config(
            ProjectConfig.E_CATE_TYPE.REDIS, ProjectConfig.E_CATE_ELE_REDIS.JOB_LIST_QUEUE_NAME
        )

    def com_queue_with_mode(self, mode: str | None) -> str:
        return self.com_queue_name + self._test_suffix(mode)

    def job_list_queue_with_mode(self, mode: str | None) -> str:
        return self.job_list_queue_name + self._test_suffix(mode)

    def _test_suffix(self, mode: str | None) -> str:
        if mode is None:
            return ""
        return self._cfg.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.TEST_SUFFIX
        )
