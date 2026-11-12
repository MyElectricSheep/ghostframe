# Contributing

Ghostframe is a research proof of concept, not a maintained product. There is no roadmap and no
promise of support.

Most welcome:

- Bug reports with a way to reproduce them: the command, the image (or how to make one), the
  profile, and your OS, CPU and torch version.
- Results from other hardware. Decoding has only been checked on x86-64 CPUs with one torch
  build; whether a GPU or an Apple CPU reads the same bits is open.
- Pull requests that fix bugs or make results easier to reproduce.

Please do not rename existing profiles. A profile's name is part of its carrier and its
authentication data, so renaming one changes the format.

Run the tests before opening a pull request:

```sh
python -m unittest discover -s tests
```

The full suite loads real models and takes a while on a CPU. `tests/test_server.py` also needs
the `server` extra.
