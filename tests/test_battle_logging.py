"""Progress semantics and CLI output separation; no server writes."""
import asyncio
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from pokegraph.sources.battles import BattleEncounter
from pokegraph_ingest.writes.battles import write_battles

ROOT = Path(__file__).resolve().parents[1]


class BattleLoggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.battles = [BattleEncounter.from_dict(json.loads(line)) for line in
                       (ROOT / 'data/corpora/red-green-blue-first-battle/battles.jsonl').read_text().splitlines()]

    def test_commit_events_only_after_success(self):
        session = AsyncMock()
        with self.assertLogs('pokegraph_ingest.battles', level='INFO') as logs:
            asyncio.run(write_battles(session, self.battles))
        self.assertEqual(session.execute_write.await_count, 16)
        commits = [message for message in logs.output if 'Committed [' in message]
        self.assertEqual(len(commits), 16)
        self.assertIn('committed=16/16', logs.output[-1])

    def test_failed_transaction_reports_previous_commits_without_secret(self):
        session = AsyncMock()
        session.execute_write.side_effect = [None, None, RuntimeError('secret-password')]
        with self.assertLogs('pokegraph_ingest.battles', level='INFO') as logs:
            with self.assertRaises(RuntimeError):
                asyncio.run(write_battles(session, self.battles))
        self.assertEqual(sum('Committed [' in message for message in logs.output), 2)
        self.assertIn('committed=2/16', logs.output[-1])
        self.assertIn(self.battles[2].id, logs.output[-1])
        self.assertNotIn('secret-password', '\n'.join(logs.output))
        self.assertNotIn('Ingestion completed', '\n'.join(logs.output))

    def test_failed_preflight_never_logs_a_commit(self):
        session = AsyncMock()
        session.execute_read.side_effect = ValueError('missing reference')
        with self.assertLogs('pokegraph_ingest.battles', level='INFO') as logs:
            with self.assertRaises(ValueError):
                asyncio.run(write_battles(session, self.battles))
        session.execute_write.assert_not_awaited()
        self.assertIn('stage=preflight', logs.output[-1])
        self.assertIn('committed=0/16', logs.output[-1])

    def cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'pokegraph_ingest.battles', *args],
                              cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT/'src')},
                              text=True, capture_output=True, check=False)

    def test_cli_stderr_logs_and_stdout_json(self):
        result = self.cli('--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['counts']['BattleEncounter'], 16)
        self.assertIn('mode=check', result.stderr)
        self.assertIn('Validation passed', result.stderr)
        self.assertIn('elapsed=', result.stderr)
        quiet = self.cli('--check', '--log-level', 'ERROR')
        self.assertEqual(quiet.returncode, 0, quiet.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(quiet.stdout))
        self.assertEqual(quiet.stderr, '')

    def test_cli_failure_exit_and_no_success_report(self):
        result = self.cli('--check', '--corpus', '/nonexistent-battle-test-corpus')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('error_type=FileNotFoundError', result.stderr)
        self.assertNotIn('pipeline completed', result.stderr)


if __name__ == '__main__':
    unittest.main()
