import threading

from raven.config import RavenConfig
from raven.core.collector import Collector


def test_collector_concurrency():
    config = RavenConfig()
    collector = Collector(config)

    results = []
    errors = []

    def target():
        try:
            snap = collector.collect()
            results.append(snap)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=target) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Clean up collector to avoid leaving threads or timers alive
    collector.close()

    assert len(errors) == 0, f"Errors occurred during concurrent collect: {errors}"
    assert len(results) == 5
    for r in results:
        assert r is not None
