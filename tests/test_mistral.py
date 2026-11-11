"""Kiểm tra adapter Mistral và hai CLI mà không gọi API thật."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))

from agent import run_agent
from providers import Provider
from status_tools import StatusTools
import run
import run_evals


class MistralProviderTests(unittest.TestCase):
    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'test-mistral-key'}, clear=True)
    def test_tool_call_round_trip_and_null_final_calls(self):
        call_id = 'aB3cdE4fG'
        assistant = {'role': 'assistant', 'content': None, 'tool_calls': [{
            'id': call_id,
            'type': 'function',
            'function': {'name': 'get_status', 'arguments': '{"provider":"github"}'},
        }]}
        replies = iter([
            {'choices': [{'message': assistant, 'finish_reason': 'tool_calls'}],
             'usage': {'total_tokens': 100}},
            {'choices': [{'message': {'role': 'assistant', 'content': 'Snapshot checked.',
                                      'tool_calls': None}, 'finish_reason': 'stop'}],
             'usage': {'total_tokens': 120}},
        ])
        requests = []

        def respond(url, headers, payload):
            requests.append((url, headers, json.loads(json.dumps(payload))))
            return next(replies)

        with patch('providers.post_json', side_effect=respond):
            result = run_agent('Check GitHub.', Provider('mistral', 'mistral-large-latest'),
                               StatusTools(), max_steps=2)

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['answer'], 'Snapshot checked.')
        self.assertEqual(result['usage'], [{'total_tokens': 100}, {'total_tokens': 120}])
        self.assertEqual(len(requests), 2)
        for url, headers, payload in requests:
            self.assertEqual(url, 'https://api.mistral.ai/v1/chat/completions')
            self.assertEqual(headers['Authorization'], 'Bearer test-mistral-key')
            self.assertEqual(payload['model'], 'mistral-large-latest')
        self.assertTrue(any(s['function']['name'] == 'get_status' for s in requests[0][2]['tools']))
        history = requests[1][2]['messages']
        self.assertEqual(history[-2], assistant)
        self.assertEqual(history[-1]['role'], 'tool')
        self.assertEqual(history[-1]['tool_call_id'], call_id)
        self.assertEqual(json.loads(history[-1]['content'])['provider'], 'github')
        self.assertNotIn('test-mistral-key', json.dumps(result))

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_key_names_mistral_variable(self):
        with self.assertRaisesRegex(ValueError, 'Thiếu MISTRAL_API_KEY'):
            Provider('mistral', 'mistral-large-latest')


class MistralCLITests(unittest.TestCase):
    @patch.dict('os.environ', {'PROVIDER': 'mistral', 'MODEL': 'mistral-large-latest'}, clear=True)
    def test_run_accepts_mistral_from_flag_and_environment(self):
        result = {'status': 'completed', 'answer': 'ok', 'trace': [], 'usage': []}
        for options in ([], ['--provider', 'mistral']):
            with self.subTest(options=options), patch.object(sys, 'argv', ['run.py', *options, 'Check status']), \
                    patch.object(run, 'run', return_value=result) as mocked, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run.main(), 0)
                self.assertEqual(mocked.call_args.args[2:4], ('mistral', 'mistral-large-latest'))

    @patch.dict('os.environ', {'PROVIDER': 'mistral', 'MODEL': 'mistral-large-latest'}, clear=True)
    def test_eval_accepts_mistral_agent_and_judge(self):
        for options in ([], ['--provider', 'mistral', '--judge-provider', 'mistral']):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'report.json'

                def fake_case(case, args):
                    self.assertEqual(args.provider, 'mistral')
                    self.assertEqual(args.judge_provider, 'mistral')
                    self.assertEqual(args.model, 'mistral-large-latest')
                    self.assertEqual(args.judge_model, 'mistral-large-latest')
                    return {'id': case['id'], 'grade': {'score': 80, 'status': 'scored'}}

                argv = ['run_evals.py', *options, '--case', 'E1', '--output', str(output)]
                with patch.object(sys, 'argv', argv), \
                        patch.object(run_evals, 'run_case', side_effect=fake_case), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(run_evals.main(), 0)
                report = json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(report['config']['provider'], 'mistral')
                self.assertEqual(report['config']['judge_provider'], 'mistral')
                self.assertEqual(report['summary']['scored_cases'], 1)


if __name__ == '__main__':
    unittest.main()
