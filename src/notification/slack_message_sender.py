from __future__ import annotations

import base64
import threading
import time
from collections import deque
from datetime import datetime, timedelta

import requests

from python_library.thread.thread import abThreading

from config.project_config import ProjectConfig
# 메시지를 큐에 모았다가 delay_time 마다 묶어 slack web hook 으로 전송.
# (실제 webhook 은 base64 로 채널/헤더/바디를 인코딩하는 사내 proxy.)
class SlackMessageSender(abThreading):
    def __init__(self) -> None:
        super().__init__()
        self._is_running = False
        self._lock = threading.Lock()
        self._send_queue: deque[str] = deque()
        self._config = ProjectConfig.instance()

        self._project_name = self._config.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.PROJECT_NAME
        )
        self._slack_url = self._config.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.SLACK_URL
        )
        self._channel = self._config.get_config(
            ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.SLACK_CHANNEL_NAME
        )
        self._send_interval = int(
            self._config.get_config(
                ProjectConfig.E_CATE_TYPE.COMMON, ProjectConfig.E_CATE_ELE_COMMON.DELAY_TIME
            )
        )
        self._send_target_time = datetime.now() + timedelta(seconds=self._send_interval)

    def send(self, slack_msg: str) -> None:
        with self._lock:
            self._send_queue.append(slack_msg)
            self._delay()

    def _delay(self) -> None:
        self._send_target_time = datetime.now() + timedelta(seconds=self._send_interval)

    def _delay_with_lock(self) -> None:
        with self._lock:
            self._delay()

    def start(self) -> None:
        if self._is_running:
            return
        super().start()  # abThread.start (Thread.start 호출)
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        super().stop()

    def action(self) -> None:
        while self._is_running:
            remaining = (self._send_target_time - datetime.now()).total_seconds()
            if remaining < 0:
                self._delay_with_lock()
                time.sleep(0.1)
                continue
            if remaining >= self._send_interval:
                with self._lock:
                    if not self._send_queue:
                        self._delay()
                        time.sleep(0.1)
                        continue
                    message = ""
                    while self._send_queue:
                        message += str(self._send_queue.popleft()) + "\n"
                    if message:
                        self._send_slack_message(message)
                    self._delay()

    def _send_slack_message(self, message: str) -> None:
        channel_b64 = base64.b64encode(self._channel.encode()).decode()
        header = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + self._project_name
        header_b64 = base64.b64encode(header.encode()).decode()
        body_b64 = base64.b64encode(message.encode()).decode()
        requests.get(url=f"{self._slack_url}{channel_b64}/{header_b64}/{body_b64}")
