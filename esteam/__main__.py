import sys
import asyncio
import argparse

from .web import serve
from .config import Config


parser = argparse.ArgumentParser(prog="esteam", add_help=False)
parser.add_argument("-c", "--config", nargs=1, type=str, help="config file.")
parser.add_argument("-h", "--host", nargs=1, default=["0.0.0.0"], help="host address.")
parser.add_argument("-p", "--port", nargs=1, default=[8000], type=int, help="host port.")


def main():
    args = parser.parse_args()
    if not args.config: return
    config = args.config[0]
    host = args.host[0]
    port = args.port[0]
    Config(config)
    serve(host=host, port=port)


if __name__ == "__main__":
    sys.exit(main())
