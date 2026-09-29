import argparse
import json
import sys
from pathlib import Path
from .core import Budget, Engine, PackError, ReplayProvider, write_outputs


def main():
    parser = argparse.ArgumentParser(description='Offline evidence-grounded subtitle review pipeline')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--pack', required=True)
    run.add_argument('--out', required=True)
    run.add_argument('--max-model-calls', type=int, default=25)
    run.add_argument('--max-tool-calls', type=int, default=50)
    run.add_argument('--simulate-failure', action='store_true')
    correction = sub.add_parser('correct')
    correction.add_argument('--state', required=True)
    correction.add_argument('--event', required=True)
    correction.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            if not 0 <= args.max_model_calls <= 25 or not 0 <= args.max_tool_calls <= 50:
                raise PackError('Call limits must be within 0..25 model and 0..50 tool calls.')
            pack = json.loads(Path(args.pack).read_text(encoding='utf-8'))
            engine = Engine(pack, ReplayProvider(args.simulate_failure), Budget(args.max_model_calls, args.max_tool_calls)).run()
        else:
            engine = Engine.restore(json.loads(Path(args.state).read_text(encoding='utf-8')))
            affected = engine.correct(json.loads(Path(args.event).read_text(encoding='utf-8')))
            print('Affected subtitle IDs:', ', '.join(affected) or 'none')
        print(json.dumps(write_outputs(engine, args.out), indent=2))
        return 0
    except (PackError, OSError, ValueError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
