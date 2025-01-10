import asyncio
import datetime
from tempfile import TemporaryDirectory
from pathlib import Path
from argparse import ArgumentParser

import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup

routes = web.RouteTableDef()

BIN_INFO_URL = "https://myaccount.stockport.gov.uk/bin-collections/show/{}/"
BIN_COLOURS = {"black", "blue", "brown", "green"}


async def get_bin_collection_dates(location_code: str) -> dict[str, datetime.date]:
    """
    Gets the next collection date of each bin
    """
    bin_info_url = BIN_INFO_URL.format(location_code)

    # We're going to be making a request about twice a week. I can totally eat
    # creating a session per request, thank you!
    async with aiohttp.ClientSession() as session:
        async with session.get(bin_info_url) as resp:
            resp.raise_for_status()
            html = await resp.text()

    out: dict[str, datetime.date] = {}

    soup = BeautifulSoup(html, "html.parser")
    for bin_soup in soup.find_all("div", class_="service-item"):
        bin_colour = bin_soup.find("h3").string.removesuffix(" bin").lower()
        if bin_colour not in BIN_COLOURS:
            raise ValueError(f"No valid bin colour found in {bin_soup}")

        for date_candidate in bin_soup.find_all("p"):
            try:
                dt = datetime.datetime.strptime(
                    date_candidate.string.strip(), "%A, %d %B %Y"
                )
            except ValueError:
                continue
            date = dt.date()
            break
        else:
            raise ValueError(f"No date found in {bin_soup}")

        out[bin_colour] = date

    if set(out) != BIN_COLOURS:
        raise ValueError(f"Unexpected bin colours: {', '.join(out)}")

    return out


class DateInPastError(Exception):
    """
    Thrown when relative_date is called with a 'now' which is after 'then'.
    """


def relative_date(now: datetime.date, then: datetime.date) -> str:
    """
    Describe the relative delta between dates 'now' and 'then' as one of:

    * today
    * tomorrow
    * monday
    * tuesday
    * wednesday
    * thursday
    * friday
    * saturday
    * sunday
    * next week
    * week after next
    * three weeks
    * very long time
    """
    if then < now:
        raise DateInPastError("Date 'then' is before date 'now'")

    if then == now:
        return "today"

    delta = (then - now).days

    if delta == 1:
        return "tomorrow"

    # Weekday
    if delta < 7:
        return then.strftime("%A").lower()

    # Make 'X week' messages tick over on sundays/mondays
    delta += now.weekday()

    # Next week
    if 7 <= delta < 14:
        return "next week"
    elif 14 <= delta < 21:
        return "week after next"
    elif 21 <= delta < 28:
        return "three weeks"
    elif 28 <= delta < 35:
        return "four weeks"

    return "very long time"


def ui_inkscape_actions(
    bins: dict[str, datetime.date],
    now: datetime.date | None = None,
) -> str:
    """
    Generate a set of Inkscape actions to put the UI into a state showing the
    relative bin dates on the specified date.
    """
    if now is None:
        now = datetime.date.today()

    enabled_selectors = []
    for bin_colour in sorted(BIN_COLOURS):
        when = relative_date(now, bins[bin_colour]).replace(" ", "-")
        print(bin_colour, bins[bin_colour], when)

        enabled_selectors.append(f".{bin_colour}.{when}")
        if when == "tomorrow":
            enabled_selectors.append(f".{bin_colour}.selected")
        if when in ("tomorrow", "today"):
            enabled_selectors.append(f".{bin_colour}.open")
        else:
            enabled_selectors.append(f".{bin_colour}.closed")

    actions = [
        f"select-by-selector: .variable;",
        f"selection-hide;",
        f"select-by-selector:\n      {'\n    , '.join(enabled_selectors)}\n    ;",
        f"selection-unhide;",
    ]

    print()
    return "\n".join(actions)


async def render_ui(
    bins: dict[str, datetime.date],
    now: datetime.date | None = None,
) -> bytes:
    """
    Return the rendered UI as a PNG image.
    """
    with TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        actions_file = tmpdir / "actions.txt"
        actions_file.write_text(ui_inkscape_actions(bins, now))

        png_file = tmpdir / "ui.png"

        process = await asyncio.create_subprocess_exec(
            f"inkscape",
            str(Path(__file__).parent / "ui.svg"),
            f"--actions-file={actions_file}",
            f"--export-dpi=96",
            f"--export-area-page",
            f"--export-png-use-dithering=false",
            f"--export-png-color-mode=Gray_1",
            f"--export-overwrite",
            f"--export-filename={png_file}",
        )
        if exit_code := await process.wait():
            raise RuntimeError(f"Inkscape returned non-zero exit code {exit_code}")

        return png_file.read_bytes()


def get_next_update(
    bins: dict[str, datetime.date], now: datetime.date | None = None
) -> datetime.date:
    """
    Get the date when the display may next change
    """
    if now is None:
        now = datetime.date.today()

    actions = ui_inkscape_actions(bins, now)
    while True:
        now += datetime.timedelta(days=1)
        try:
            if actions == ui_inkscape_actions(bins, now):
                continue
        except DateInPastError:
            pass
        break

    return now


@routes.get("/")
async def get_index(request: web.Request) -> web.Response:
    bins = await get_bin_collection_dates(request.app["location_code"])
    png = await render_ui(bins)

    # Set the X-Next-Update header such that the display will sleep until 3am
    # the day the display is next due to change. By picking 3am, we avoid
    # having to think about how the Stockport bins website handles daylight
    # saving.
    next_update_date = get_next_update(bins)
    delta = (
        datetime.datetime.combine(next_update_date, datetime.time(3, 0, 0))
        - datetime.datetime.now()
    )
    next_update_seconds = int(max(delta.total_seconds(), 60 * 60))

    return web.Response(
        body=png,
        headers={
            "Content-Type": "image/png",
            "X-Next-Update": str(next_update_seconds),
        },
    )


def main() -> None:
    parser = ArgumentParser()

    parser.add_argument(
        "--location-code",
        "-l",
        type=str,
        required=True,
        help="""
            The Stockport council API location code to fetch the bin collection
            timetable for.
        """,
    )
    parser.add_argument(
        "--host",
        "-H",
        default="0.0.0.0",
        type=str,
        help="""
            The IP to listen on. Default: %(default)s.
        """,
    )
    parser.add_argument(
        "--port",
        "-P",
        default=8080,
        type=int,
        help="""
            The port to run the web server on.
        """,
    )

    args = parser.parse_args()

    app = web.Application()
    app.add_routes(routes)
    app["location_code"] = args.location_code
    web.run_app(
        app,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
