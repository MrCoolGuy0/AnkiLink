"""A held network job must leave Anki's serialized collection worker available.

The executor split/default matches Anki 25.9.2 aqt/taskman.py. These are bounded
worker-isolation tests, not a benchmark of the user's Windows collection.
"""
from concurrent.futures import ThreadPoolExecutor
import threading
import types
import unittest
import test_message_controller as base


class TaskQueues:
    def __init__(self):
        self.collection = ThreadPoolExecutor(max_workers=1)
        self.other = ThreadPoolExecutor(max_workers=2)
        self.completions = []
        self.flags = []
        self.lock = threading.Lock()

    def run_in_background(self, work, done=None, uses_collection=True):
        self.flags.append(uses_collection)
        future = (self.collection if uses_collection else self.other).submit(work)
        if done:
            def enqueue(future):
                with self.lock:
                    self.completions.append((done, future))
            future.add_done_callback(enqueue)
        return future

    def close(self):
        self.collection.shutdown(wait=True)
        self.other.shutdown(wait=True)


class BackgroundJobs(unittest.TestCase):
    setUp = base.MessageController.setUp

    def test_pending_http_leaves_next_card_worker_available(self):
        queues = TaskQueues()
        self.c.mw.taskman = queues
        entered, release = threading.Event(), threading.Event()
        def network():
            entered.set()
            if not release.wait(3):
                raise TimeoutError('Test did not release network job')
            return 'server reply'
        try:
            self.c.run(network)
            self.assertTrue(entered.wait(1))
            native = queues.run_in_background(lambda: 'next card')
            self.assertEqual(native.result(timeout=.5), 'next card')
            self.assertFalse(release.is_set(), 'Network must still be pending')
            self.assertEqual(queues.flags, [False, True])
        finally:
            release.set()
            queues.close()

    def test_network_flag_keeps_success_failure_and_epoch_guards(self):
        flags = []
        def enqueue(work, done, *, uses_collection=True):
            flags.append(uses_collection)
            self.jobs.append((work, done))
        self.c.mw.taskman = types.SimpleNamespace(run_in_background=enqueue)
        self.c.run(lambda: 'reply', lambda value: self.events.append(value))
        base.MessageController.finish(self, 0)
        self.c.run(lambda: 1/0, failure=lambda error: self.events.append(error))
        base.MessageController.finish(self, 1)
        self.c.run(lambda: 'stale', lambda value: self.events.append(value))
        self.c.epoch += 1
        base.MessageController.finish(self, 2)
        self.assertEqual(flags, [False, False, False])
        self.assertEqual(self.events, ['reply', 'division by zero'])


if __name__ == '__main__':
    unittest.main()
