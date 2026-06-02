import unittest
import time
from unittest.mock import patch
from gui.core.resilience import run_with_retries_and_timeout

class TestResilience(unittest.TestCase):
    def test_successful_run(self):
        result = run_with_retries_and_timeout(["echo", "hello"], max_attempts=1, timeout_sec=2)
        self.assertTrue(result)

    def test_timeout_and_retry(self):
        with patch('gui.core.resilience.time.sleep') as mock_sleep:
            start = time.time()
            result = run_with_retries_and_timeout(["sleep", "1"], max_attempts=2, timeout_sec=0.2)
            duration = time.time() - start
            self.assertFalse(result)
            self.assertTrue(duration < 1.0)
            mock_sleep.assert_any_call(4)

    def test_failure_retry(self):
        with patch('gui.core.resilience.time.sleep') as mock_sleep:
            result = run_with_retries_and_timeout(["false"], max_attempts=2, timeout_sec=1)
            self.assertFalse(result)
            mock_sleep.assert_any_call(4)

    def test_line_callback(self):
        lines = []
        def cb(line):
            lines.append(line.strip())
        
        result = run_with_retries_and_timeout(["echo", "testline"], max_attempts=1, timeout_sec=2, line_callback=cb)
        self.assertTrue(result)
        self.assertIn("testline", lines)

if __name__ == '__main__':
    unittest.main()
