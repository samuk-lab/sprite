# 1000 Genomes 20-sample high-coverage 4-chromosome test subset

This directory contains a small, regional 1000 Genomes high-coverage test dataset.

## Samples

- 10 GBR samples: HG00096, HG00097, HG00099, HG00100, HG00101, HG00102, HG00103, HG00105, HG00106, HG00107
- 10 YRI samples: NA18486, NA18488, NA18489, NA18498, NA18499, NA18501, NA18502, NA18504, NA18505, NA18507

## Regions

The base region specs are:

- region_spec	bam_region	vcf_region
- 2:10000000-10049999	chr2:10000000-10049999	chr2:10000000-10049999
- 7:50000000-50049999	chr7:50000000-50049999	chr7:50000000-50049999
- 12:25000000-25049999	chr12:25000000-25049999	chr12:25000000-25049999
- 20:10000000-10049999	chr20:10000000-10049999	chr20:10000000-10049999

BAM extraction regions and targets.bed are written to match the detected BAM/CRAM contig style.
VCF regions are chr-prefixed to match the high-coverage VCF files.

## Coverage

The source CRAMs are NYGC high-coverage, approximately 30x whole-genome data.
This script uses DOWNSAMPLE_FRAC=0.67, so the regional BAMs are
approximately 30x * 0.67. Set DOWNSAMPLE_FRAC=1 to keep full depth.

## Files

- `samples.tsv`: wisp-mask sample metadata
- `sample_populations.tsv`: sample/population metadata
- `sample_populations_and_sources.tsv`: sample/population/source CRAM metadata
- `samples.list`: sample list used for VCF subsetting
- `regions.bam.txt`: BAM/CRAM interval list using detected BAM contig names
- `regions.vcf.txt`: VCF interval list using chr-prefixed contig names
- `regions.paired.tsv`: mapping between base specs, BAM regions, and VCF regions
- `targets.bed`: BED intervals matching the BAM contig style
- `bams/*.bam`: one regional BAM per sample, containing reads from all target intervals
- `1000g_20samples_highcov.vcf.gz`: one multi-sample VCF for all 20 samples and all four regions

