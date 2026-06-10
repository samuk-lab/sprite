#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

SCRIPT_VERSION="2026-05-28-wisp-test-data-20samples-4chroms-v6-github-size-guard"

# download_1000g_20sample_4chrom_highcov_fixture.sh
#
# macOS/Linux-compatible script to:
#   1. Create/reuse a conda environment using mamba/micromamba/libmamba only.
#   2. Download a small high-coverage 1000 Genomes two-population dataset.
#
# Dataset:
#   - 20 regional BAMs: 10 GBR + 10 YRI
#   - one indexed multi-sample VCF containing all 20 samples
#   - four 50 kb regions from four different chromosomes
#   - samples.tsv metadata for wisp-mask
#   - targets.bed for the selected regions
#
# Important contig-name behavior:
#   - The script detects whether the source CRAMs use "20" or "chr20".
#   - BAM extraction regions and targets.bed are written to match the BAM/CRAM contigs.
#   - VCF extraction regions remain chr-prefixed because the high-coverage VCF files are chr-prefixed.
#
# Requirements:
#   - macOS or Linux
#   - bash
#   - conda+mamba, micromamba, or conda with --solver libmamba
#
# Usage:
#   bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#
# Optional:
#   ENV_NAME=wisp-test-data bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#   OUTDIR=tests/test_data/1000g_20sample_highcov_4chrom_subset bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#   THREADS=4 bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#   DOWNSAMPLE_FRAC=1 bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#   FORCE=1 bash tests/test_data/scripts/download_1000g_20sample_4chrom_highcov_fixture.sh
#
# Notes:
#   - Relative paths are resolved from the repository root.
#   - Source CRAMs are 1000 Genomes / NYGC ~30x GRCh38 CRAMs.
#   - Local alignments are written as BAMs so downstream tests do not need CRAM reference handling.
#   - The script does not use conda activate. It uses conda run -p or micromamba run -p.
#   - htslib's CRAM reference cache is stored outside the fixture directory by
#     default so large reference slices are not accidentally committed.

ENV_NAME="${ENV_NAME:-wisp-test-data}"
OUTDIR="${OUTDIR:-tests/test_data/1000g_20sample_highcov_4chrom_subset}"
THREADS="${THREADS:-2}"
FORCE="${FORCE:-0}"

# GitHub warns on files larger than 50 MiB and blocks files larger than 100 MiB.
# Keep generated fixtures below the warning threshold by default. Override only
# for local experiments that will not be committed.
MAX_GITHUB_FILE_BYTES="${MAX_GITHUB_FILE_BYTES:-52428800}"

if [ -n "${XDG_CACHE_HOME:-}" ]; then
    DEFAULT_REF_CACHE_DIR="${XDG_CACHE_HOME}/wisp-test-data/ref_cache"
else
    DEFAULT_REF_CACHE_DIR="${HOME}/.cache/wisp-test-data/ref_cache"
fi
REF_CACHE_DIR="${REF_CACHE_DIR:-${DEFAULT_REF_CACHE_DIR}}"

# Set to 1 for full ~30x. Default 0.67 gives roughly 20x from 30x source data.
DOWNSAMPLE_FRAC="${DOWNSAMPLE_FRAC:-0.67}"
DOWNSAMPLE_SEED="${DOWNSAMPLE_SEED:-42}"

SEQUENCE_INDEX_URL="https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000G_2504_high_coverage/1000G_2504_high_coverage.sequence.index"

# Four 50 kb intervals, defined as chrom_number:start-end in GRCh38 coordinates.
# BAM regions are generated from these using the detected BAM contig style.
# VCF regions are generated from these with chr-prefixed contigs.
REGION_SPECS=(
  "2:10000000-10049999"
  "7:50000000-50049999"
  "12:25000000-25049999"
  "20:10000000-10049999"
)

SAMPLES=(
  "HG00096 GBR"
  "HG00097 GBR"
  "HG00099 GBR"
  "HG00100 GBR"
  "HG00101 GBR"
  "HG00102 GBR"
  "HG00103 GBR"
  "HG00105 GBR"
  "HG00106 GBR"
  "HG00107 GBR"
  "NA18486 YRI"
  "NA18488 YRI"
  "NA18489 YRI"
  "NA18498 YRI"
  "NA18499 YRI"
  "NA18501 YRI"
  "NA18502 YRI"
  "NA18504 YRI"
  "NA18505 YRI"
  "NA18507 YRI"
)

# Set by create_env_and_runner.
ENV_PREFIX=""
RUNNER_KIND=""
CREATE_TOOL=""

# Set after CRAM header inspection. Either "chr" or "".
BAM_CHROM_PREFIX=""

die() {
    echo "ERROR: $*" >&2
    exit 1
}

info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_os() {
    case "$(uname -s)" in
        Darwin|Linux) ;;
        *) die "This script supports macOS and Linux only." ;;
    esac
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

create_env_and_runner() {
    info "Script version: ${SCRIPT_VERSION}"
    info "Environment name: ${ENV_NAME}"

    if command_exists conda && command_exists mamba; then
        CONDA_BASE="$(conda info --base)"
        ENV_PREFIX="${CONDA_BASE}/envs/${ENV_NAME}"
        CREATE_TOOL="mamba"
        RUNNER_KIND="conda"

        if [ ! -d "${ENV_PREFIX}" ]; then
            info "Creating environment with mamba at: ${ENV_PREFIX}"
            mamba create -y \
                -p "${ENV_PREFIX}" \
                -c conda-forge \
                -c bioconda \
                python=3.11 \
                curl \
                samtools \
                bcftools \
                htslib \
                mosdepth \
                bedtools
        else
            info "Environment prefix already exists: ${ENV_PREFIX}"
        fi
        return
    fi

    if command_exists micromamba; then
        ENV_PREFIX="${PWD}/.conda_envs/${ENV_NAME}"
        CREATE_TOOL="micromamba"
        RUNNER_KIND="micromamba"

        if [ ! -d "${ENV_PREFIX}" ]; then
            info "Creating environment with micromamba at: ${ENV_PREFIX}"
            micromamba create -y \
                -p "${ENV_PREFIX}" \
                -c conda-forge \
                -c bioconda \
                python=3.11 \
                curl \
                samtools \
                bcftools \
                htslib \
                mosdepth \
                bedtools
        else
            info "Environment prefix already exists: ${ENV_PREFIX}"
        fi
        return
    fi

    if command_exists conda; then
        if ! conda create --help 2>/dev/null | grep -q -- "--solver"; then
            die "conda is installed, but it does not expose --solver. Install mamba/micromamba or a conda version with the libmamba solver."
        fi

        CONDA_BASE="$(conda info --base)"
        ENV_PREFIX="${CONDA_BASE}/envs/${ENV_NAME}"
        CREATE_TOOL="conda --solver libmamba"
        RUNNER_KIND="conda"

        if [ ! -d "${ENV_PREFIX}" ]; then
            info "Creating environment with conda --solver libmamba at: ${ENV_PREFIX}"
            conda create --solver libmamba -y \
                -p "${ENV_PREFIX}" \
                -c conda-forge \
                -c bioconda \
                python=3.11 \
                curl \
                samtools \
                bcftools \
                htslib \
                mosdepth \
                bedtools
        else
            info "Environment prefix already exists: ${ENV_PREFIX}"
        fi
        return
    fi

    die "mamba, micromamba, or conda with --solver libmamba is required."
}

run_in_env() {
    if [ "${RUNNER_KIND}" = "conda" ]; then
        conda run --no-capture-output -p "${ENV_PREFIX}" "$@"
    elif [ "${RUNNER_KIND}" = "micromamba" ]; then
        micromamba run -p "${ENV_PREFIX}" "$@"
    else
        die "internal error: RUNNER_KIND is not set"
    fi
}

validate_tools() {
    run_in_env curl --version >/dev/null
    run_in_env samtools --version >/dev/null
    run_in_env bcftools --version >/dev/null
    run_in_env mosdepth --version >/dev/null
    run_in_env bedtools --version >/dev/null

    info "Environment prefix: ${ENV_PREFIX}"
    info "Environment created with: ${CREATE_TOOL}"
    info "samtools: $(run_in_env samtools --version | head -n 1)"
    info "bcftools: $(run_in_env bcftools --version | head -n 1)"
}

download_sequence_index() {
    mkdir -p "${OUTDIR}/sources"
    index_path="${OUTDIR}/sources/1000G_2504_high_coverage.sequence.index"

    if [ "${FORCE}" != "1" ] && [ -s "${index_path}" ]; then
        info "Sequence index already exists, skipping: ${index_path}"
    else
        info "Downloading high-coverage sequence index"
        run_in_env curl -L --fail --retry 3 --retry-delay 5 \
            -o "${index_path}.tmp" \
            "${SEQUENCE_INDEX_URL}"
        mv "${index_path}.tmp" "${index_path}"
    fi
}

normalize_cram_url() {
    raw="$1"

    case "${raw}" in
        https://*) printf "%s\n" "${raw}" ;;
        http://*) printf "%s\n" "${raw}" ;;
        ftp://ftp.sra.ebi.ac.uk/*) printf "%s\n" "${raw/ftp:\/\//https:\/\/}" ;;
        ftp.sra.ebi.ac.uk/*) printf "https://%s\n" "${raw}" ;;
        /vol1/run/*) printf "https://ftp.sra.ebi.ac.uk%s\n" "${raw}" ;;
        vol1/run/*) printf "https://ftp.sra.ebi.ac.uk/%s\n" "${raw}" ;;
        *) die "Do not know how to normalize CRAM URL/path: ${raw}" ;;
    esac
}

lookup_cram_url() {
    sample="$1"
    index_path="${OUTDIR}/sources/1000G_2504_high_coverage.sequence.index"

    raw="$(
        awk -v sample="${sample}" '
            BEGIN { FS="\t" }
            $0 ~ sample && $0 ~ /\.cram/ {
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /\.cram$/ || $i ~ /\.cram[[:space:]]*$/) {
                        print $i
                        exit
                    }
                }
            }
        ' "${index_path}" | head -n 1
    )"

    if [ -z "${raw}" ]; then
        die "Could not find CRAM path for sample ${sample} in ${index_path}"
    fi

    normalize_cram_url "${raw}"
}

download_local_crai() {
    sample="$1"
    cram_url="$2"
    crai_url="${cram_url}.crai"
    local_crai="${OUTDIR}/sources/${sample}.final.cram.crai"

    # IMPORTANT:
    # This function is used in command substitutions like:
    #   local_crai="$(download_local_crai ...)"
    # Therefore it must print ONLY the final CRAI path to stdout.
    # All logging must go to stderr, or samtools -X will receive a garbage path.

    if [ "${FORCE}" != "1" ] && [ -s "${local_crai}" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] CRAI already exists, skipping: ${local_crai}" >&2
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloading CRAI for ${sample}" >&2
        echo "[$(date '+%Y-%m-%d %H:%M:%S')]   source: ${crai_url}" >&2
        run_in_env curl -L --fail --silent --show-error --retry 3 --retry-delay 5 \
            -o "${local_crai}.tmp" \
            "${crai_url}"
        mv "${local_crai}.tmp" "${local_crai}"
    fi

    printf "%s\n" "${local_crai}"
}

configure_cram_reference_cache() {
    cleanup_legacy_fixture_ref_cache
    mkdir -p "${REF_CACHE_DIR}"

    export REF_CACHE="${REF_CACHE_DIR}/%2s/%2s/%s"
    export REF_PATH="${REF_CACHE}:https://www.ebi.ac.uk/ena/cram/md5/%s"
    info "CRAM reference cache: ${REF_CACHE_DIR}"
}

cleanup_legacy_fixture_ref_cache() {
    legacy_cache="${OUTDIR}/ref_cache"
    if [ -d "${legacy_cache}" ]; then
        info "Removing legacy in-fixture CRAM reference cache: ${legacy_cache}"
        rm -rf "${legacy_cache}"
    fi
}

check_generated_file_sizes() {
    info "Checking generated fixture files are <= ${MAX_GITHUB_FILE_BYTES} bytes"
    too_large_file="$(find "${OUTDIR}" -type f -size +"${MAX_GITHUB_FILE_BYTES}"c -print -quit)"
    if [ -n "${too_large_file}" ]; then
        size_bytes="$(wc -c < "${too_large_file}" | tr -d ' ')"
        die "generated file exceeds MAX_GITHUB_FILE_BYTES (${MAX_GITHUB_FILE_BYTES}): ${too_large_file} (${size_bytes} bytes)"
    fi
}

detect_bam_contig_style() {
    first_entry="${SAMPLES[0]}"
    read -r sample pop <<< "${first_entry}"
    cram_url="$(lookup_cram_url "${sample}")"
    local_crai="$(download_local_crai "${sample}" "${cram_url}")"

    info "Detecting BAM/CRAM contig naming using ${sample}"
    info "  source: ${cram_url}"
    info "  index:  ${local_crai}"

    header_file="${OUTDIR}/sources/${sample}.cram.header.sam"

    if [ "${FORCE}" != "1" ] && [ -s "${header_file}" ]; then
        info "CRAM header already exists, using: ${header_file}"
    else
        # Use -X to force samtools to use the local CRAI. This avoids slow or
        # unreliable remote index discovery.
        run_in_env samtools view -H -X "${cram_url}" "${local_crai}" > "${header_file}.tmp"
        mv "${header_file}.tmp" "${header_file}"
    fi

    if awk -F'\t' '$1=="@SQ" { for (i=1; i<=NF; i++) if ($i=="SN:chr20") found=1 } END { exit(found ? 0 : 1) }' "${header_file}"; then
        BAM_CHROM_PREFIX="chr"
    elif awk -F'\t' '$1=="@SQ" { for (i=1; i<=NF; i++) if ($i=="SN:20") found=1 } END { exit(found ? 0 : 1) }' "${header_file}"; then
        BAM_CHROM_PREFIX=""
    else
        die "Could not detect whether CRAM uses chr20 or 20 contigs from ${header_file}"
    fi

    if [ -z "${BAM_CHROM_PREFIX}" ]; then
        info "Detected BAM/CRAM contig style: no chr prefix, e.g. 20"
    else
        info "Detected BAM/CRAM contig style: chr prefix, e.g. chr20"
    fi
}

bam_region_from_spec() {
    spec="$1"
    chrom="${spec%%:*}"
    range="${spec#*:}"
    printf "%s%s:%s\n" "${BAM_CHROM_PREFIX}" "${chrom}" "${range}"
}

vcf_region_from_spec() {
    spec="$1"
    chrom="${spec%%:*}"
    range="${spec#*:}"
    printf "chr%s:%s\n" "${chrom}" "${range}"
}

vcf_url_for_region_spec() {
    spec="$1"
    chrom="${spec%%:*}"
    printf "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000G_2504_high_coverage/working/20220422_3202_phased_SNV_INDEL_SV/1kGP_high_coverage_Illumina.chr%s.filtered.SNV_INDEL_SV_phased_panel.vcf.gz\n" "${chrom}"
}

write_targets_and_regions() {
    mkdir -p "${OUTDIR}"

    : > "${OUTDIR}/targets.bed"
    : > "${OUTDIR}/regions.bam.txt"
    : > "${OUTDIR}/regions.vcf.txt"
    : > "${OUTDIR}/regions.paired.tsv"

    printf "region_spec\tbam_region\tvcf_region\n" > "${OUTDIR}/regions.paired.tsv"

    for spec in "${REGION_SPECS[@]}"; do
        chrom="${spec%%:*}"
        range="${spec#*:}"
        start="${range%-*}"
        end="${range#*-}"

        case "${start}" in
            ''|*[!0-9]*) die "Region start must be numeric: ${spec}" ;;
        esac
        case "${end}" in
            ''|*[!0-9]*) die "Region end must be numeric: ${spec}" ;;
        esac
        if [ "${start}" -gt "${end}" ]; then
            die "Region start must be <= region end: ${spec}"
        fi

        bam_chrom="${BAM_CHROM_PREFIX}${chrom}"
        bam_region="$(bam_region_from_spec "${spec}")"
        vcf_region="$(vcf_region_from_spec "${spec}")"
        bed_start=$((start - 1))

        printf "%s\t%s\t%s\n" "${bam_chrom}" "${bed_start}" "${end}" >> "${OUTDIR}/targets.bed"
        printf "%s\n" "${bam_region}" >> "${OUTDIR}/regions.bam.txt"
        printf "%s\n" "${vcf_region}" >> "${OUTDIR}/regions.vcf.txt"
        printf "%s\t%s\t%s\n" "${spec}" "${bam_region}" "${vcf_region}" >> "${OUTDIR}/regions.paired.tsv"
    done
}

write_metadata_files() {
    mkdir -p "${OUTDIR}/bams"

    {
        printf "sample_id\tpopulation\talignment\n"
        for entry in "${SAMPLES[@]}"; do
            read -r sample pop <<< "${entry}"
            printf "%s\t%s\t%s\n" "${sample}" "${pop}" "${OUTDIR}/bams/${sample}.bam"
        done
    } > "${OUTDIR}/samples.tsv"

    {
        for entry in "${SAMPLES[@]}"; do
            read -r sample pop <<< "${entry}"
            printf "%s\n" "${sample}"
        done
    } > "${OUTDIR}/samples.list"

    {
        printf "sample_id\tpopulation\n"
        for entry in "${SAMPLES[@]}"; do
            read -r sample pop <<< "${entry}"
            printf "%s\t%s\n" "${sample}" "${pop}"
        done
    } > "${OUTDIR}/sample_populations.tsv"
}

write_source_metadata_with_crams() {
    {
        printf "sample_id\tpopulation\tsource_cram\n"
        for entry in "${SAMPLES[@]}"; do
            read -r sample pop <<< "${entry}"
            cram_url="$(lookup_cram_url "${sample}")"
            printf "%s\t%s\t%s\n" "${sample}" "${pop}" "${cram_url}"
        done
    } > "${OUTDIR}/sample_populations_and_sources.tsv"
}

samtools_downsample_arg() {
    frac="$1"

    case "${frac}" in
        1|1.0|1.00) printf "" ;;
        0.*) printf "%s.%s" "${DOWNSAMPLE_SEED}" "${frac#0.}" ;;
        .*) printf "%s.%s" "${DOWNSAMPLE_SEED}" "${frac#.}" ;;
        *) die "DOWNSAMPLE_FRAC must be between 0 and 1, e.g. 0.67 or 1" ;;
    esac
}

download_bam_regions() {
    sample="$1"
    pop="$2"
    cram_url="$3"
    local_crai="$(download_local_crai "${sample}" "${cram_url}")"
    out_bam="${OUTDIR}/bams/${sample}.bam"
    sample_tmp_dir="${OUTDIR}/tmp_bams/${sample}"

    if [ "${FORCE}" != "1" ] && [ -s "${out_bam}" ] && [ -s "${out_bam}.bai" ]; then
        info "BAM already exists, skipping: ${out_bam}"
        return
    fi

    info "Downloading regional BAM for ${sample} (${pop})"
    info "  source: ${cram_url}"
    info "  downsample fraction: ${DOWNSAMPLE_FRAC}"
    info "  strategy: extract one region at a time, then merge"

    rm -f "${out_bam}" "${out_bam}.bai"
    rm -rf "${sample_tmp_dir}"
    mkdir -p "${sample_tmp_dir}"

    downsample_arg="$(samtools_downsample_arg "${DOWNSAMPLE_FRAC}")"
    part_list="${sample_tmp_dir}/parts.list"
    : > "${part_list}"

    region_i=0
    for spec in "${REGION_SPECS[@]}"; do
        region_i=$((region_i + 1))
        bam_region="$(bam_region_from_spec "${spec}")"
        safe_region="${bam_region/:/_}"
        safe_region="${safe_region//:/_}"
        part_bam="${sample_tmp_dir}/${sample}.${safe_region}.bam"

        info "  ${sample}: extracting BAM region ${region_i}/${#REGION_SPECS[@]}: ${bam_region}"

        if [ -z "${downsample_arg}" ]; then
            run_in_env samtools view \
                -@ "${THREADS}" \
                -b \
                -o "${part_bam}" \
                -X "${cram_url}" "${local_crai}" \
                "${bam_region}"
        else
            run_in_env samtools view \
                -@ "${THREADS}" \
                -b \
                -s "${downsample_arg}" \
                -o "${part_bam}" \
                -X "${cram_url}" "${local_crai}" \
                "${bam_region}"
        fi

        run_in_env samtools quickcheck -v "${part_bam}"

        part_size="$(wc -c < "${part_bam}" | tr -d ' ')"
        part_reads="$(run_in_env samtools view -c "${part_bam}")"
        info "  ${sample}: wrote ${part_bam} (${part_size} bytes, ${part_reads} reads)"

        if [ "${part_reads}" = "0" ]; then
            die "${part_bam} has zero reads. Check contig naming, region choice, and source CRAM/index."
        fi

        printf "%s\n" "${part_bam}" >> "${part_list}"
    done

    info "  ${sample}: merging ${#REGION_SPECS[@]} regional BAM chunks"

    run_in_env samtools merge \
        -@ "${THREADS}" \
        -f \
        -b "${part_list}" \
        "${out_bam}"

    run_in_env samtools quickcheck -v "${out_bam}"
    run_in_env samtools index -@ "${THREADS}" "${out_bam}"

    final_size="$(wc -c < "${out_bam}" | tr -d ' ')"
    info "  ${sample}: final BAM ${out_bam} (${final_size} bytes)"

    if [ "${KEEP_TMP_BAMS:-0}" != "1" ]; then
        rm -rf "${sample_tmp_dir}"
    fi
}

download_multisample_vcf_regions() {
    mkdir -p "${OUTDIR}/tmp_vcfs"

    tmp_list="${OUTDIR}/tmp_vcfs/vcf_parts.list"
    : > "${tmp_list}"

    for spec in "${REGION_SPECS[@]}"; do
        vcf_region="$(vcf_region_from_spec "${spec}")"
        safe_region="${vcf_region/:/_}"
        safe_region="${safe_region//:/_}"
        out_part="${OUTDIR}/tmp_vcfs/1000g_20samples_highcov.${safe_region}.vcf.gz"
        url="$(vcf_url_for_region_spec "${spec}")"

        if [ "${FORCE}" != "1" ] && [ -s "${out_part}" ] && [ -s "${out_part}.tbi" ]; then
            info "VCF part already exists, skipping: ${out_part}"
        else
            info "Downloading multi-sample VCF region: ${vcf_region}"
            info "  source: ${url}"

            rm -f "${out_part}" "${out_part}.tbi"

            run_in_env bcftools view \
                -r "${vcf_region}" \
                -S "${OUTDIR}/samples.list" \
                -Oz \
                -o "${out_part}" \
                "${url}"

            run_in_env bcftools index -t "${out_part}"
        fi

        printf "%s\n" "${out_part}" >> "${tmp_list}"
    done

    out_vcf="${OUTDIR}/1000g_20samples_highcov_4chroms.vcf.gz"

    if [ "${FORCE}" != "1" ] && [ -s "${out_vcf}" ] && [ -s "${out_vcf}.tbi" ]; then
        info "Combined VCF already exists, skipping: ${out_vcf}"
    else
        info "Concatenating VCF parts into one multi-sample VCF"
        rm -f "${out_vcf}" "${out_vcf}.tbi"

        run_in_env bcftools concat \
            -a \
            -f "${tmp_list}" \
            -Oz \
            -o "${out_vcf}"

        run_in_env bcftools index -t "${out_vcf}"
    fi

    ln -sf "$(basename "${out_vcf}")" "${OUTDIR}/1000g_20samples_highcov.vcf.gz"
    ln -sf "$(basename "${out_vcf}.tbi")" "${OUTDIR}/1000g_20samples_highcov.vcf.gz.tbi"
}

write_dataset_readme() {
    cat > "${OUTDIR}/README.md" <<EOF
# 1000 Genomes 20-sample high-coverage 4-chromosome test subset

This directory contains a small, regional 1000 Genomes high-coverage test dataset.

## Samples

- 10 GBR samples: HG00096, HG00097, HG00099, HG00100, HG00101, HG00102, HG00103, HG00105, HG00106, HG00107
- 10 YRI samples: NA18486, NA18488, NA18489, NA18498, NA18499, NA18501, NA18502, NA18504, NA18505, NA18507

## Regions

The base region specs are:

$(sed 's/^/- /' "${OUTDIR}/regions.paired.tsv")

BAM extraction regions and targets.bed are written to match the detected BAM/CRAM contig style.
VCF regions are chr-prefixed to match the high-coverage VCF files.

## Coverage

The source CRAMs are NYGC high-coverage, approximately 30x whole-genome data.
This script uses DOWNSAMPLE_FRAC=${DOWNSAMPLE_FRAC}, so the regional BAMs are
approximately 30x * ${DOWNSAMPLE_FRAC}. Set DOWNSAMPLE_FRAC=1 to keep full depth.

## Files

- \`samples.tsv\`: wisp sample metadata
- \`sample_populations.tsv\`: sample/population metadata
- \`sample_populations_and_sources.tsv\`: sample/population/source CRAM metadata
- \`samples.list\`: sample list used for VCF subsetting
- \`regions.bam.txt\`: BAM/CRAM interval list using detected BAM contig names
- \`regions.vcf.txt\`: VCF interval list using chr-prefixed contig names
- \`regions.paired.tsv\`: mapping between base specs, BAM regions, and VCF regions
- \`targets.bed\`: BED intervals matching the BAM contig style
- \`bams/*.bam\`: one regional BAM per sample, containing reads from all target intervals
- \`1000g_20samples_highcov.vcf.gz\`: one multi-sample VCF for all 20 samples and all four regions

## GitHub size guard

Generated files are checked against MAX_GITHUB_FILE_BYTES=${MAX_GITHUB_FILE_BYTES}
bytes. htslib's CRAM reference cache is stored outside this fixture directory:

\`${REF_CACHE_DIR}\`

EOF
}

main() {
    check_os
    create_env_and_runner
    validate_tools

    mkdir -p "${OUTDIR}/bams" "${OUTDIR}/sources"

    download_sequence_index
    configure_cram_reference_cache
    detect_bam_contig_style
    write_targets_and_regions
    write_metadata_files
    write_source_metadata_with_crams

    for entry in "${SAMPLES[@]}"; do
        read -r sample pop <<< "${entry}"
        cram_url="$(lookup_cram_url "${sample}")"
        download_bam_regions "${sample}" "${pop}" "${cram_url}"
    done

    download_multisample_vcf_regions
    write_dataset_readme
    check_generated_file_sizes

    echo
    info "Done."
    echo "Environment name:   ${ENV_NAME}"
    echo "Environment prefix: ${ENV_PREFIX}"
    echo "Output dir:         ${OUTDIR}"
    echo "Samples TSV:        ${OUTDIR}/samples.tsv"
    echo "Targets BED:        ${OUTDIR}/targets.bed"
    echo "BAM regions:        ${OUTDIR}/regions.bam.txt"
    echo "VCF regions:        ${OUTDIR}/regions.vcf.txt"
    echo "Multi VCF:          ${OUTDIR}/1000g_20samples_highcov.vcf.gz"
}

main "$@"
