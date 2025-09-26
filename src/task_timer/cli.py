import argparse
import sys

from .task_timer import TaskTimer, TaskTimerError


def main(argv=None):
    parser = argparse.ArgumentParser(description="TaskTimer CLI")
    parser.add_argument('--task', default='default', help='Task name to manage')
    parser.add_argument('--state-file', default=None, help='File to persist timer state as JSON')
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start the timer")
    stop_parser = subparsers.add_parser("stop", help="Stop the timer")
    report_parser = subparsers.add_parser("report", help="Report the timer")
    report_parser.add_argument("--format", choices=["json", "table"], default="table")

    args = parser.parse_args(argv)
    try:
        timer = TaskTimer(state_file=args.state_file)
    except Exception as e:
        print(f"Error: Failed to load state file: {e}", file=sys.stderr)
        return 2
    try:
        if args.command == "start":
            timer.start(task=args.task)
            print(f"Started timer for task: {args.task}")
        elif args.command == "stop":
            timer.stop(task=args.task)
            print(f"Stopped timer for task: {args.task}")
        elif args.command == "report":
            out = timer.to_report(
                task=args.task,
                output_format=getattr(args, 'format', 'table'),
            )
            print(out)
        else:
            parser.print_help(sys.stderr)
            return 2
    except TaskTimerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
