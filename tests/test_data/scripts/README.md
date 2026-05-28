# Test data scripts

These scripts generate or refresh the 1000 Genomes test fixtures used by the
integration tests. They live beside the fixture data instead of in the
repository root because they are test-data maintenance tools, not package entry
points.

Run them from anywhere; each script changes to the repository root before doing
work so default relative paths stay stable.

```bash
bash tests/test_data/scripts/download_1000g_10sample_chr20_highcov_fixture.sh
bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
```

Outputs are written under `tests/test_data/` by default. Override `OUTDIR`,
`THREADS`, `DOWNSAMPLE_FRAC`, or `FORCE` when refreshing a fixture.

Generated fixture files are checked against `MAX_GITHUB_FILE_BYTES`, which
defaults to 52,428,800 bytes (50 MiB). GitHub warns on regular Git files above
50 MiB and blocks files above 100 MiB, so the default keeps refreshed fixtures
below the warning threshold.

The scripts read remote CRAM files. htslib may need to cache reference slices
for those CRAMs, and those slices can be larger than GitHub's per-file limit.
By default, the cache is written outside the fixture directory at
`${XDG_CACHE_HOME:-$HOME/.cache}/sprite-test-data/ref_cache`. Override
`REF_CACHE_DIR` if you want a different local cache location.
