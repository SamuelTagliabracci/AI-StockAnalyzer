"""Insider trades via SEC Form 4 — the live 'shadow the big players' source.

Corporate insiders (directors, officers, 10%+ owners) must file a Form 4 within 2
business days of trading their own company's stock. We pull recent Form 4s per company,
parse the structured XML, and keep only open-market buys (code P) and sells (code S) —
grants/gifts (price 0) are compensation noise, not conviction signals.
"""
import xml.etree.ElementTree as ET

from signals.sec import cik_for, get

# Open-market transaction codes worth surfacing. P = purchase, S = sale.
_ACTION = {"P": "BUY", "S": "SELL"}


def _filings(cik: str, limit: int):
    """Yield (accession, primaryDocument, filingDate) for recent Form 4s."""
    import json
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    rec = sub["filings"]["recent"]
    seen = 0
    for i, form in enumerate(rec["form"]):
        if form != "4":
            continue
        yield rec["accessionNumber"][i], rec["primaryDocument"][i], rec["filingDate"][i]
        seen += 1
        if seen >= limit:
            return


def _parse(raw: str):
    """Extract (owner, role, code, acq/disp, date, shares, price) rows from one Form 4."""
    root = ET.fromstring(raw)
    owner = root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or "Insider"
    rel = root.find(".//reportingOwner/reportingOwnerRelationship")
    role = "Insider"
    if rel is not None:
        if (rel.findtext("isDirector") or "").lower() in ("1", "true"):
            role = "Director"
        if rel.findtext("officerTitle"):
            role = rel.findtext("officerTitle")
        elif (rel.findtext("isTenPercentOwner") or "").lower() in ("1", "true"):
            role = "10% Owner"
    for t in root.findall(".//nonDerivativeTransaction"):
        code = t.findtext(".//transactionCoding/transactionCode")
        if code not in _ACTION:
            continue
        yield {
            "owner": owner,
            "role": role,
            "action": _ACTION[code],
            "date": t.findtext(".//transactionDate/value"),
            "shares": t.findtext(".//transactionAmounts/transactionShares/value"),
            "price": t.findtext(".//transactionAmounts/transactionPricePerShare/value"),
        }


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def ingest(db, symbols, per_company: int = 30) -> int:
    """Pull recent insider trades for each symbol into market_signals. Returns rows written."""
    written = 0
    for sym in symbols:
        cik = cik_for(sym)
        if not cik:
            continue  # non-US issuer (e.g. .TO) — no Form 4 on EDGAR
        cik_int = int(cik)
        for accession, primary_doc, filing_date in _filings(cik, per_company):
            acc_nodash = accession.replace("-", "")
            doc = primary_doc.split("/")[-1]  # raw XML lives at accession root
            url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
            try:
                rows = list(_parse(get(url).decode("utf-8", "replace")))
            except (ET.ParseError, Exception):
                continue
            for idx, r in enumerate(rows):
                shares, price = _to_float(r["shares"]), _to_float(r["price"])
                ok = db.add_market_signal({
                    "source": "insider",
                    "symbol": sym,
                    "actor": r["owner"].title(),
                    "actor_role": r["role"],
                    "action": r["action"],
                    "shares": shares,
                    "value_usd": (shares * price) if (shares and price) else None,
                    "price": price,
                    "traded_at": r["date"],
                    "filed_at": filing_date,
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/",
                    "external_id": f"{accession}-{idx}",
                })
                if ok:
                    written += 1
    return written
