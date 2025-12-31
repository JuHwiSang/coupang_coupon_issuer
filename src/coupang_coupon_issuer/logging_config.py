"""로깅 설정 모듈

애플리케이션 전체의 로깅을 일관되게 관리합니다.
- 콘솔: INFO 레벨 (사용자용)
- 파일: DEBUG 레벨 (전체 로그)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> None:
    """
    애플리케이션 로깅 설정
    
    Args:
        log_file: 로그 파일 경로 (None이면 파일 로깅 비활성화)
        console_level: 콘솔 출력 레벨 (기본: INFO)
        file_level: 파일 출력 레벨 (기본: DEBUG)
    """
    # Root logger 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()
    
    # 포맷터 정의
    # 콘솔: 간단한 포맷 (사용자 친화적)
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일: 상세 포맷 (디버깅용)
    file_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (INFO 레벨)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 (DEBUG 레벨)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 logger 반환
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
    
    Returns:
        설정된 Logger 인스턴스
    """
    return logging.getLogger(name)
