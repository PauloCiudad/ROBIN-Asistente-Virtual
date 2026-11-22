import sys


def main() -> int:
    from robin.app import run

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
