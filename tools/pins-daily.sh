#!/bin/zsh
# The mini's morning run for the Pinterest feed (tools/pins.py): add the day's pins to pins/ideas.xml and push.
# Pinterest reads the feed about once a day and pins the new items. Only the feed is committed here; images, page and
# plan are made on the MacBook. launchd com.swiftian.if-pins-daily 07:10; log ~/Mini/data/site-watch/logs/if-pins-daily.out.log
# Each run starts with a [YYYY-MM-DD HH:MM] line and says FAIL: on error (watch tools/bin/job-check reads both).
cd "${0:A:h}/.." || exit 1
echo "[$(date '+%F %H:%M')] if-pins-daily"
fail() { echo "FAIL: $1"; exit 1; }
git pull -q --rebase || fail "git pull"
python3 tools/pins.py feed || fail "pins.py feed"
if ! git diff --quiet -- pins/ideas.xml; then
  git add pins/ideas.xml
  git -c user.name=Swiftian -c user.email=classymotion@gmail.com commit -q -m "Pinterest feed for $(date +%F) (tools/pins-daily.sh on the mini)" || fail "commit"
  git push -q || fail "git push"
  echo "pushed"
else
  echo "no new pins today"
fi
