#!/bin/sh
# 뭉클이 게이트웨이 감시견 — ★ 컨테이너 "밖"에서 본다
#
# 왜 밖인가 : 2026-09-13, 게이트웨이가 자기를 재시작하다 s6-svc -d 에서 죽었고
#             s6-svc -u 가 영원히 실행되지 않아 40분간 정지했다 (E-249 · E-252).
#             안에 있는 감시는 같이 죽는다 (E-215).
# 무엇을 보나: s6-svstat. docker ps 는 "Up" 이라고 답한다 — 컨테이너는 살아 있으니까 (E-254).
# 설치       : VPS 호스트의 root crontab, 1분마다.
# 일부러 내릴 때: 이 크론을 먼저 끄십시오. 안 그러면 1분 뒤 다시 올라옵니다.
#
# 2026-09-13 안토니우스 작성.

LOG=/root/gw-watchdog.log
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
S=$(docker exec hermes-vps /command/s6-svstat /run/service/gateway-default 2>&1)

case "$S" in
  up*)
      exit 0                                   # 정상 — 아무것도 하지 않는다. 로그도 안 쓴다
      ;;
  down*)
      echo "$NOW DOWN  : $S"            >> "$LOG"
      docker exec hermes-vps /command/s6-svc -u /run/service/gateway-default 2>>"$LOG"
      echo "$NOW REVIVE: s6-svc -u 보냄" >> "$LOG"
      ;;
  *)
      # docker exec 자체가 실패 = 컨테이너가 죽었거나 사라졌다.
      # ★ 컨테이너는 자동으로 켜지 않는다 — 사람이 봐야 하는 일이다.
      echo "$NOW UNKNOWN: $S"           >> "$LOG"
      ;;
esac
