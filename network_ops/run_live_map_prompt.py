"""
통합 인프라 프롬프트 실행기.
WHY: 패키지 상대 import 가 동작하도록 network_ops 를 sys.path 에 올린 뒤 모듈을 띄웁니다.

  cd network_ops
  python run_live_map_prompt.py
  python run_live_map_prompt.py -f live_map/hosts.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from live_map.infra_prompt import main

if __name__ == "__main__":
    raise SystemExit(main())
