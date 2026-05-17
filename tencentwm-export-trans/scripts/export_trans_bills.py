#!/usr/bin/env python3
"""Export Tencent Wealth Management (理财通) transaction bills to CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

API_URL = (
    "https://www.tencentwm.com/fbp/fund/v1/"
    "trpc.com.tencent.fit.fubillplat.query.vo.facade."
    "FubillplatQueryVoService.QueryTransBillList"
)

DEFAULT_REFERER = "https://www.tencentwm.com/web/v3/account/trans_detail.shtml"

CSV_FIELDS = [
    "acc_time",
    "bill_name",
    "bill_fee_yuan",
    "bill_sub_desc",
    "bill_busi_type",
    "bill_state",
    "bill_show_state",
    "fund_code",
    "spid",
    "fund_brief_name",
    "fund_date",
    "bill_listid",
    "asset_change_type",
    "plain_unit",
    "bill_unit",
    "bill_unit_text",
]


def fetch_page(
    cookie: str,
    *,
    start_date: str,
    end_date: str,
    page_info: str,
    bill_busi_qry_type: int = 0,
    time_type: int = 1,
) -> dict[str, Any]:
    body = {
        "start_date": start_date,
        "end_date": end_date,
        "year_month": "",
        "time_type": time_type,
        "bill_busi_qry_type": bill_busi_qry_type,
        "page_info": page_info,
    }
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("Cookie", cookie)
    req.add_header("Referer", DEFAULT_REFERER)
    req.add_header("Origin", "https://www.tencentwm.com")
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Accept", "text/plain, */*; q=0.01")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_bills(
    cookie: str,
    *,
    start_date: str,
    end_date: str,
    initial_page_info: str,
    max_pages: int = 500,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    all_bills: list[dict[str, Any]] = []
    page_info = initial_page_info
    seen_cursors: set[str] = set()

    for page_num in range(1, max_pages + 1):
        result = fetch_page(
            cookie,
            start_date=start_date,
            end_date=end_date,
            page_info=page_info,
        )

        retcode = str(result.get("retcode", ""))
        if retcode != "0":
            raise RuntimeError(
                f"API error on page {page_num}: retcode={retcode}, "
                f"retmsg={result.get('retmsg', '')}"
            )

        bills = result.get("bill_list") or []
        if not bills:
            if verbose:
                print(f"Page {page_num}: no more records", file=sys.stderr)
            break

        all_bills.extend(bills)
        next_cursor = result.get("page_info") or ""

        if verbose:
            print(
                f"Page {page_num}: +{len(bills)} rows (total {len(all_bills)}), "
                f"next={next_cursor[:60]}{'...' if len(next_cursor) > 60 else ''}",
                file=sys.stderr,
            )

        if not next_cursor or next_cursor in seen_cursors:
            break

        seen_cursors.add(next_cursor)
        page_info = next_cursor

    return all_bills


def bill_to_row(bill: dict[str, Any]) -> dict[str, Any]:
    row = {field: bill.get(field, "") for field in CSV_FIELDS}
    fee = bill.get("bill_fee")
    row["bill_fee_yuan"] = round(float(fee) / 100, 2) if fee not in (None, "") else ""
    return row


def write_csv(bills: list[dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for bill in bills:
            writer.writerow(bill_to_row(bill))


def resolve_cookie(args: argparse.Namespace) -> str:
    cookie = (args.cookie or os.environ.get("TENCENTWM_COOKIE") or "").strip()
    if not cookie:
        raise SystemExit(
            "Cookie is required. Pass --cookie, set TENCENTWM_COOKIE, "
            "or use --cookie-file."
        )
    return cookie


def resolve_cookie_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def build_parser() -> argparse.ArgumentParser:
    today = datetime.now().strftime("%Y%m%d")
    parser = argparse.ArgumentParser(
        description="Export Tencent WM (理财通) transaction bills to CSV.",
    )
    parser.add_argument(
        "-c",
        "--cookie",
        help="Request Cookie header value (or set env TENCENTWM_COOKIE).",
    )
    parser.add_argument(
        "--cookie-file",
        help="Read cookie from a local file (first line or entire file).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"tencentwm_trans_bills_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        help="Output CSV path (default: tencentwm_trans_bills_<timestamp>.csv).",
    )
    parser.add_argument(
        "--start-date",
        default="20140101",
        help="Query start date, YYYYMMDD (default: 20140101).",
    )
    parser.add_argument(
        "--end-date",
        default=today,
        help=f"Query end date, YYYYMMDD (default: {today}).",
    )
    parser.add_argument(
        "--page-info",
        default='{"accTime":""}',
        help='Pagination cursor JSON, e.g. \'{"accTime":"2026-05-07 07:30:26"}\'. '
        'Use empty accTime for the first page.',
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="Safety limit for pagination (default: 500).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print pagination progress to stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cookie_file:
        cookie = resolve_cookie_file(args.cookie_file)
    else:
        cookie = resolve_cookie(args)

    try:
        bills = fetch_all_bills(
            cookie,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_page_info=args.page_info,
            max_pages=args.max_pages,
            verbose=args.verbose,
        )
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    write_csv(bills, args.output)
    print(f"Exported {len(bills)} rows -> {os.path.abspath(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
