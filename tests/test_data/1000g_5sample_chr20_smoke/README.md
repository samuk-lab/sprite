# 1000G 5-sample chr20 smoke fixture

Tiny workflow smoke fixture using five existing BAMs from the chr20 subset.

- `samples.tsv`: three GBR samples and two YRI samples
- `targets.bed`: 10 kb chr20 interval

The fixture is intended to check that the CLI runs end to end and writes only
the compressed population-count BED plus its tabix index. The larger
`1000g_20sample_highcov_4chrom_subset` fixture is the main integration test.
