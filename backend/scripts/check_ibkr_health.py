#!/usr/bin/env python3
import sys, datetime, traceback, logging
from ib_insync import IB, util

TRACE = False # True         # flip to False to silence
SSL   = True
LIVE_PORT, PAPER_PORT = (4001, 4002) if SSL else (7496, 7497)
LIVE_ID, PAPER_ID     = 201, 101

def probe(name, host, port, client_id, timeout=10.0, readonly=False):
    ib = IB()

    if TRACE:
        util.logToConsole()                 # ib_insync internal logs
        logging.getLogger().setLevel(logging.DEBUG)

        # Print IB API errors with codes (so 321 is obvious)
        def on_error(reqId, code, msg, _json=''):
            print(f"[{name}] IB error {code} (reqId {reqId}): {msg}")
        ib.errorEvent += on_error

    try:
        ib.connect(host, port, clientId=client_id, timeout=timeout, readonly=readonly)
        now = ib.reqCurrentTime()
        return True, f"Connected {host}:{port}, serverTime={now}"
    except Exception as e:
        if TRACE: traceback.print_exc()
        return False, f"FAILED {host}:{port} -> {e}"
    finally:
        try: ib.disconnect()
        except Exception: pass

def main():
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok_paper, msg_paper = probe("PAPER", "127.0.0.1", PAPER_PORT, PAPER_ID, readonly=True)
    ok_live,  msg_live  = probe("LIVE",  "127.0.0.1", LIVE_PORT,  LIVE_ID,  readonly=True)
    print(f"[{ts}] PAPER: {msg_paper}")
    print(f"[{ts}]  LIVE: {msg_live}")
    if not (ok_paper and ok_live):
        sys.exit(1)

if __name__ == "__main__":
    main()

###   Original working version

#import sys, datetime
#from ib_insync import IB

#LIVE_PORT  = 4001 # 7496
#PAPER_PORT = 4002 # 7497
#LIVE_ID    = 201
#PAPER_ID   = 101

#def probe(host, port, client_id):
#    ib = IB()
#    try:
#        ib.connect(host, port, clientId=client_id, timeout=5)
#        now = ib.reqCurrentTime()
#        ib.disconnect()
#        return True, f"Connected {host}:{port}, serverTime={now}"
#    except Exception as e:
#        try:
#            ib.disconnect()
#        except Exception:
#            pass
#        return False, f"FAILED {host}:{port} -> {e}"

#def main():
#    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#    ok_paper, msg_paper = probe('127.0.0.1', PAPER_PORT, PAPER_ID)
#    ok_live,  msg_live  = probe('127.0.0.1', LIVE_PORT,  LIVE_ID)
#    print(f"[{ts}] PAPER: {msg_paper}")
#    print(f"[{ts}]  LIVE: {msg_live}")
#    # Exit non-zero if either failed (lets LaunchAgent log it distinctly)
#    if not (ok_paper and ok_live):
#        sys.exit(1)

#if __name__ == "__main__":
#    main()

