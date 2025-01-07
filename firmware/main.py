import sys

from badger2040 import (
    WIDTH,
    HEIGHT,
    UPDATE_NORMAL,
    Badger2040,
    sleep_for,
)
from pngdec import PNG
import mrequests
from WIFI_CONFIG import BIN_SERVER_URL

badger = Badger2040()

try:
    exp_backoff_minutes = 1
    while True:
        badger.connect()

        try:
            r = mrequests.get(BIN_SERVER_URL, save_headers=True)

            if r.status_code != 200:
                raise Exception(f"Status {r.status_code}!")

            png = PNG(badger.display)
            png.open_RAM(r.content)

            badger.set_update_speed(UPDATE_NORMAL)
            png.decode(0, 0)
            badger.update()

            # Get the time until the next scheduled change of the display
            for header_bytes in r.headers:
                key, _, value = header_bytes.decode("ascii").partition(":")
                if key.lower().strip() == "X-Next-Update".lower():
                    next_update_minutes = int(value.strip()) // 60
                    break
            else:
                next_update_minutes = 24 * 60

            # Reset exponential backoff (success)
            exp_backoff_minutes = 1
        except Exception as exc:
            sys.print_exception(exc)

            badger.display.set_pen(15)
            badger.display.clear()

            badger.display.set_pen(0)
            badger.display.text("Oh dear...", 0, 0)
            badger.display.text(type(exc).__name__, 0, 20)
            badger.display.text(str(exc), 0, 40, wordwrap=WIDTH)
            badger.update()

            # Exponentially back off before retrying
            next_update_minutes = exp_backoff_minutes
            exp_backoff_minutes = min(24 * 60, exp_backoff_minutes * 2)

        print(f"Sleeping for {next_update_minutes} minutes...")
        sleep_for(next_update_minutes)
finally:
    # In case we get stuck in a crash loop, stay asleep for long periods so we
    # don't just drain the battery!
    sleep_for(24 * 60)
