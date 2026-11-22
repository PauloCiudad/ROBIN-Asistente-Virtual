import sys


def _run_script(argv: list[str]) -> int:
    """`ROBIN.exe --run-script <archivo.py> [args]`: ejecuta una automatización con el Python incluido.

    En la versión instalada no hay un Python aparte, así que ROBIN se usa a sí mismo como intérprete.
    """
    import runpy

    index = argv.index("--run-script")
    script = argv[index + 1]
    sys.argv = [script, *argv[index + 2:]]
    runpy.run_path(script, run_name="__main__")
    return 0


def main() -> int:
    if "--run-script" in sys.argv:
        return _run_script(sys.argv)
    from robin.app import run

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
