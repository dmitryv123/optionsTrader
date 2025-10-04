# portfolio/management/commands/sync_ibkr.py
import os
import sys
from decimal import Decimal
from typing import Dict, Tuple
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from ib_insync import IB, util, Contract, Stock, Option  # pip install ib-insync

from accounts.models import Client, BrokerAccount, AccountSnapshot
from portfolio.models import (
    Portfolio, Instrument, IbkrContract, Position, Order, Execution
)

def decimal_safe(x) -> Decimal:
    try:
        if x is None: return Decimal("0")
        if isinstance(x, Decimal): return x
        return Decimal(str(x))
    except Exception:
        return Decimal("0")

def asset_type_from_secType(secType: str) -> str:
    secType = (secType or "").upper()
    return {
        "STK": "equity",
        "ETF": "etf",
        "OPT": "option",
        "FUT": "future",
        "CASH": "fx",
        "CRYPTO": "crypto",
    }.get(secType, "equity")

def get_or_create_instrument_from_contract(c) -> Instrument:
    """
    Create a generic Instrument for the contract's symbol / secType.
    For options, we still create an Instrument with asset_type='option' using the underlier symbol.
    """
    asset_type = asset_type_from_secType(c.secType)
    symbol = c.symbol or c.localSymbol or (c.conId and str(c.conId)) or "UNKNOWN"
    exchange = c.exchange or ""
    currency = c.currency or "USD"
    name = ""
    inst, _ = Instrument.objects.get_or_create(
        symbol=symbol,
        asset_type=asset_type,
        currency=currency,
        defaults={"name": name, "exchange": exchange, "is_active": True},
    )
    # Lightly update if exchange changed
    if inst.exchange != exchange and exchange:
        inst.exchange = exchange
        inst.save(update_fields=["exchange"])
    return inst

def upsert_ibkr_contract(c, instrument: Instrument) -> IbkrContract:
    ic, created = IbkrContract.objects.get_or_create(
        con_id=c.conId,
        defaults={
            "instrument": instrument,
            "sec_type": c.secType,
            "exchange": c.exchange or "",
            "currency": c.currency or "USD",
            "local_symbol": c.localSymbol or "",
            "last_trade_date_or_contract_month": getattr(c, "lastTradeDateOrContractMonth", "") or "",
            "strike": decimal_safe(getattr(c, "strike", None)),
            "right": getattr(c, "right", "") or "",
            "multiplier": int(getattr(c, "multiplier", 0) or 0),
            "metadata": {},
        },
    )
    # keep instrument consistent if first bind was missing
    if not created and ic.instrument_id != instrument.id:
        ic.instrument = instrument
        ic.save(update_fields=["instrument"])
    return ic

def ensure_mirror_portfolio(broker_account: BrokerAccount) -> Portfolio:
    """
    Ensure each BrokerAccount has a default portfolio to attach mirrored positions/orders.
    """
    name = "Broker Mirror"
    pf, _ = Portfolio.objects.get_or_create(
        client=broker_account.client,
        broker_account=broker_account,
        name=name,
        defaults={"base_currency": broker_account.base_currency, "metadata": {"auto": True}},
    )
    return pf


class Command(BaseCommand):
    help = "Mirror IBKR account summary, positions, orders, and executions into local DB (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--host", default=os.getenv("IB_HOST", "127.0.0.1"))
        parser.add_argument("--port", type=int, default=int(os.getenv("IB_PORT", "7497")))
        parser.add_argument("--client-id", type=int, default=int(os.getenv("IB_CLIENT_ID", "42")))
        parser.add_argument("--accounts", default="", help="Comma-separated list of IBKR account codes to sync (e.g., U12345,DU1234567). If empty, sync all linked live/paper accounts in DB.")
        parser.add_argument("--timeout", type=float, default=10.0, help="Network timeout in seconds")
        parser.add_argument("--skip-orders", action="store_true",
                            help="Skip fetching orders/executions (useful in TWS/GW Read-Only mode)")

    def handle(self, *args, **opts):
        host = opts["host"]
        port = opts["port"]
        clientId = opts["client_id"]
        wanted_accounts = {a.strip() for a in opts["accounts"].split(",") if a.strip()}

        # 1) Connect to TWS/Gateway
        ib = IB()
        self.stdout.write(self.style.NOTICE(f"Connecting to IBKR at {host}:{port} clientId={clientId}..."))
        try:
            ib.connect(host, port, clientId=clientId, timeout=opts["timeout"])
        except Exception as e:
            raise CommandError(f"Failed to connect to IBKR: {e}")

        # Managed accounts (strings like 'U1234567','DUxxxxxxx')
        managed = set(ib.managedAccounts())
        self.stdout.write(self.style.SUCCESS(f"Managed accounts from IB: {sorted(managed)}"))

        # 2) Which BrokerAccounts to sync?
        q = BrokerAccount.objects.filter(kind__in=["IBKR", "IBKR-PAPER"])
        if wanted_accounts:
            q = q.filter(account_code__in=wanted_accounts)
        broker_accounts = list(q)

        if not broker_accounts:
            self.stdout.write(self.style.WARNING("No BrokerAccount(kind in {IBKR, IBKR-PAPER}) to sync."))
            ib.disconnect()
            return

        # 3) Preload all Trades once (contains orders+fills)
        trades = []
        open_orders = []
        if not opts["skip_orders"]:
            trades = ib.trades()
            open_orders = ib.openOrders()

        # 4) Loop per broker account
        for ba in broker_accounts:
            if ba.account_code and ba.account_code not in managed:
                self.stdout.write(self.style.WARNING(f"Skipping {ba.account_code}: not in IB managed accounts list"))
                continue

            self.stdout.write(self.style.NOTICE(f"Syncing account {ba.account_code or ba.nickname} ({ba.kind})"))

            # Ensure default portfolio
            portfolio = ensure_mirror_portfolio(ba)

            # 4.1 Account Summary -> AccountSnapshot
            try:
                # accountSummary() returns a list of AccountValue, we can read by tag
                summary = ib.accountSummary(ba.account_code) if ba.account_code else []
                summary_map: Dict[str, str] = {row.tag: row.value for row in summary}
                # Common tags: 'AvailableFunds', 'BuyingPower', 'MaintMarginReq', 'FullMaintMarginReq', 'FullInitMarginReq', 'ExcessLiquidity', ...
                snap_kwargs = dict(
                    client=ba.client,
                    broker_account=ba,
                    asof_ts=timezone.now(),
                    currency=summary_map.get("Currency", ba.base_currency) or ba.base_currency,
                    cash=decimal_safe(summary_map.get("TotalCashValue")),
                    buying_power=decimal_safe(summary_map.get("BuyingPower")),
                    maintenance_margin=decimal_safe(summary_map.get("MaintMarginReq") or summary_map.get("FullMaintMarginReq")),
                    used_margin=decimal_safe(summary_map.get("InitMarginReq") or summary_map.get("FullInitMarginReq")),
                    extras={"raw": {k: summary_map.get(k) for k in summary_map.keys()}},
                )
                AccountSnapshot.objects.create(**snap_kwargs)
                self.stdout.write(self.style.SUCCESS("  AccountSnapshot inserted"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  AccountSummary fetch failed ({e}); inserting minimal snapshot"))
                AccountSnapshot.objects.create(
                    client=ba.client, broker_account=ba, asof_ts=timezone.now(),
                    currency=ba.base_currency, cash=Decimal("0"), buying_power=Decimal("0"),
                    maintenance_margin=Decimal("0"), used_margin=Decimal("0"),
                    extras={"note": "summary failed"}
                )

            # 4.2 Positions
            try:
                pos_list = [p for p in ib.positions() if getattr(p, "account", None) == ba.account_code]
                inserted = 0
                for p in pos_list:
                    c = p.contract
                    inst = get_or_create_instrument_from_contract(c)
                    ic = upsert_ibkr_contract(c, inst)

                    Position.objects.create(
                        client=ba.client,
                        portfolio=portfolio,
                        broker_account=ba,
                        instrument=inst,
                        ibkr_con=ic,
                        qty=decimal_safe(p.position),
                        avg_cost=decimal_safe(p.avgCost),
                        market_price=Decimal("0"),
                        market_value=Decimal("0"),
                        asof_ts=timezone.now(),
                    )
                    inserted += 1
                self.stdout.write(self.style.SUCCESS(f"  Positions snapshot: {inserted} rows"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Positions fetch failed: {e}"))

            # 4.3 Orders & Executions (from trades())
            if not opts["skip_orders"]:
                try:
                    # Filter trades for this account
                    acct_trades = [t for t in trades if getattr(t.order, "account", None) == ba.account_code]

                    # First pass: upsert Orders
                    for t in acct_trades:
                        c = t.contract
                        inst = get_or_create_instrument_from_contract(c)
                        ic = upsert_ibkr_contract(c, inst)
                        o = t.order

                        ord_obj, created = Order.objects.get_or_create(
                            client=ba.client,
                            broker_account=ba,
                            ibkr_con=ic,
                            ibkr_order_id=o.orderId,
                            defaults={
                                "parent_ibkr_order_id": getattr(o, "parentId", None),
                                "side": "BUY" if getattr(o, "action", "BUY").upper().startswith("B") else "SELL",
                                "order_type": getattr(o, "orderType", "") or "",
                                "limit_price": decimal_safe(getattr(o, "lmtPrice", None)),
                                "aux_price": decimal_safe(getattr(o, "auxPrice", None)),
                                "tif": getattr(o, "tif", "") or "",
                                "status": getattr(t.orderStatus, "status", "") or "",
                                "raw": {
                                    "order": util.treeToJson(o),
                                    "status": util.treeToJson(t.orderStatus),
                                },
                                "created_ts": timezone.now(),
                                "updated_ts": timezone.now(),
                            }
                        )
                        if not created:
                            # update changing fields
                            changed = False
                            status = getattr(t.orderStatus, "status", "") or ""
                            if ord_obj.status != status:
                                ord_obj.status = status; changed = True
                            ord_obj.updated_ts = timezone.now(); changed = True
                            if changed:
                                ord_obj.save(update_fields=["status", "updated_ts"])

                    # Second pass: upsert Executions (fills)
                    exec_count = 0
                    for t in acct_trades:
                        for f in t.fills:
                            e = f.execution  # has execId, time, cumQty, price etc.
                            # Find the Order we inserted above
                            # Note: some rare cases might not match due to parent/child splits.
                            try:
                                order_obj = Order.objects.get(
                                    broker_account=ba, ibkr_order_id=t.order.orderId
                                )
                            except Order.DoesNotExist:
                                continue

                            exec_obj, created = Execution.objects.get_or_create(
                                client=ba.client,
                                order=order_obj,
                                ibkr_exec_id=e.execId,
                                defaults={
                                    "fill_ts": e.time.replace(tzinfo=timezone.utc) if hasattr(e.time, "tzinfo") else timezone.now(),
                                    "qty": decimal_safe(e.shares),
                                    "price": decimal_safe(e.price),
                                    "fee": decimal_safe(getattr(f, "commissionReport", None) and getattr(f.commissionReport, "commission", None)),
                                    "venue": getattr(e, "exchange", "") or "",
                                    "raw": {
                                        "execution": util.treeToJson(e),
                                        "commission": util.treeToJson(getattr(f, "commissionReport", None)),
                                    }
                                }
                            )
                            if created:
                                exec_count += 1
                            self.stdout.write(self.style.SUCCESS(f"  Orders/Executions upserted (fills: {exec_count})"))

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  Orders/Executions fetch failed: {e}"))

        ib.disconnect()
        self.stdout.write(self.style.SUCCESS("✅ IBKR mirror complete."))
