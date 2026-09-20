"""Part G — Collection Performance Audit: stage별 실행 시간을 structured log로 남긴다.

측정만 하는 유틸이며 어떤 collection/baseline/enrichment 로직도 바꾸지 않는다 — 기존
함수 호출을 이 컨텍스트 매니저로 감싸기만 한다 (G-01).
"""

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("adcatcher.collection_timing")
logger.setLevel(logging.INFO)
if not logger.handlers:
    # uvicorn은 root logger에 handler를 붙이지 않으므로, 이 전용 로거에 직접
    # StreamHandler를 달아 앱 전역 로깅 설정과 무관하게 항상 출력되게 한다.
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [timing] %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False


@contextmanager
def stage_timer(stage: str, **context):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        ctx = " ".join(f"{k}={v}" for k, v in context.items())
        logger.info("stage=%s ms=%.0f %s", stage, elapsed_ms, ctx)
