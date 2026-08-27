"""
STATUS: stub, Day 6+. The production entrypoint: runs continuously, pulling one event at a
time off the ingest queue (src/vasooli/ingest/queue.py) and calling
orchestrator.run_one() per event — the exact same function `scripts/run_demo.py` calls in a
batch loop. Nothing about classify/decide/execute/audit changes between the demo path and
this one; only how events arrive does.

    from .ingest.queue import dequeue
    from .orchestrator import run_one
    from .audit.audit_log import AuditLog
    from .models import FailureEvent

    def main():
        audit = AuditLog()
        while True:
            payload = dequeue()
            if payload is None:
                continue
            event = FailureEvent(**payload)   # after real ingest normalizes the webhook shape
            try:
                run_one(event, audit)
            except Exception as e:
                from .audit.dead_letter import write as dlq_write
                dlq_write(record_id=event.record_id, stage="worker", error=str(e))

    if __name__ == "__main__":
        main()
"""
