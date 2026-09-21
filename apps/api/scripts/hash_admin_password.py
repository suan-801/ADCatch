"""ADMIN_PASSWORD_HASH 값을 생성하는 CLI 헬퍼.

원본 비밀번호는 .env/커밋 어디에도 남기지 않는다 — 이 스크립트로 bcrypt hash만 생성해
ADMIN_PASSWORD_HASH에 붙여넣는다.

사용법:
  cd apps/api && python -m scripts.hash_admin_password
  (인자 없이 실행하면 터미널에 숨김 입력(getpass)으로 비밀번호를 받는다)
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.admin_auth import hash_password


def run() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Admin password: ")
    if not password:
        print("비밀번호를 입력해주세요.", file=sys.stderr)
        sys.exit(1)
    print(hash_password(password))


if __name__ == "__main__":
    run()
