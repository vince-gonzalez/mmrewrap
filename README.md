# mmrewrap

Rewrap the comments in a Metamath database without the C `metamath` binary.

```
python cli.py set.mm --check      report comments that are not rewrapped
python cli.py set.mm --in-place   rewrap them
```

## Why

`scripts/rewrap` in set.mm is ten lines of shell that shell out to the compiled
`metamath` binary. A contributor without a local build wraps comments by hand, and a
reviewer asks again on the next pull request. That is a toolchain dependency sitting in
front of a formatting rule.

This is the same algorithm in pure Python, with no build step and no binary.

## What it refuses, and why that is the point

Comments this implementation does not model are never touched, and every one is named on
stderr. It does not guess, and it does not stay quiet about what it skipped.

Measured against the whole of set.mm:

| population | total | accepted | byte-exact | refused |
|---|---:|---:|---:|---:|
| statement comments | 50,685 | 50,554 | **50,554** | 131 |
| section headers | 1,317 | 0 | — | 1,317 |
| other (file headers) | 3,353 | 0 | — | 3,353 |
| **all** | 55,355 | 50,554 | **100.0000%** | 4,801 |

100.0000% byte-exact on the population it accepts. 4,801 refusals, each one reported
rather than silently mangled.

A tool that produced a confident answer for all 55,355 would be easier to write and worse
to trust.

## Verifying

`selftest.py` and `verify_ship.py` run the comparison. You supply the `.mm` database;
they are not vendored here.

## Note on excluded files

The working directory this came from also contained metamath-exe C sources and several
upstream `.mm` databases. Neither is included: the C is GPL and not mine, and the
databases belong to their projects. Fetch them from upstream.
