"""Copy-trading leaders (eToro etc.) — STUB.

The closest source to 'best individual traders on the internet'. There is no official free
API exposing leaders' live trades; pulling it means scraping a platform whose ToS likely
forbids automated access. Deferred pending a sanctioned data source or an explicit
decision to proceed. Schema + feed slot are ready.
"""


def ingest(db, symbols, **_) -> int:
    print("  [copytrade] STUB — no sanctioned free API; ToS-sensitive scraping deferred; 0 written")
    return 0
