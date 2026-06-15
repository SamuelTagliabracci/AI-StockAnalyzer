"""Congressional trades via the STOCK Act — STUB.

Senators and Representatives disclose trades within ~45 days. The free community feeds we
relied on (house/senate-stock-watcher S3 buckets) now return AccessDenied, and the
official House/Senate disclosures are PDFs (House) or session-gated search (Senate).
A real implementation needs either a paid aggregator API (Quiver, Unusual Whales) or a
PDF/HTML scraper. Schema + feed slot are ready; drop in a source to light this up.
"""


def ingest(db, symbols, **_) -> int:
    print("  [congress] STUB — free feeds went dark; needs an aggregator API key; 0 written")
    return 0
