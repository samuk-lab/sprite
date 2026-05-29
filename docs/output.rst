Output Files
************

Final outputs
=============

Each successful run writes two final files to ``--out``:

.. code-block:: text

   sprite.bed.gz
   sprite.bed.gz.tbi

The BED is bgzip-compressed and indexed with ``tabix -p bed``.
Set ``--output-prefix`` to choose a different output filename prefix; ``.bed.gz``
is appended to the prefix.

BED columns
===========

The final BED starts with comment-prefixed headers:

.. code-block:: text

   #sprite_mask_metadata  {"columns":["chrom","start","end","GBR","YRI"],...}
   #chrom  start  end  GBR  YRI

Data rows contain:

**chrom**
    Chromosome or contig name.

**start**
    0-based BED start coordinate.

**end**
    0-based BED end coordinate, exclusive.

**population columns**
    Number of samples in each population with depth greater than or equal to
    ``--threshold`` over the interval.

Adjacent bases with identical population counts are collapsed. Intervals where
all counts are zero are omitted.

Metadata
========

The ``#sprite_mask_metadata`` line is JSON. It includes:

* ``sprite_mask_version``
* ``format``
* ``columns``
* ``coordinate_system``
* ``zero_count_intervals_omitted``
* ``threshold``
* ``sample_count``
* ``populations``
* ``population_columns``
* ``population_sample_counts``
* input paths such as ``samples_path``, ``popfile``, ``all_sites_vcf``, and
  ``targets_bed`` when applicable

Sparse interpretation
=====================

The final BED is sparse by design. A missing interval means zero passing
samples in every population. It does not mean the interval was skipped by the
writer or that counts are unknown.

Intermediate files
==================

When ``--keep-work`` is set, BAM/CRAM mode keeps files like:

.. code-block:: text

   targets.3col.bed
   targets.3col.sorted.merged.bed
   <sample>.d<threshold>.quantized.bed.gz
   <sample>.d<threshold>.quantized.bed.gz.csi
   <sample>.d<threshold>.mosdepth.summary.txt
   <sample>.d<threshold>.mosdepth.global.dist.txt
   <sample>.d<threshold>.mosdepth.stderr.log
   <sample>.d<threshold>.pass.bed
   <sample>.d<threshold>.pass.targets.bed
   cohort.d<threshold>.multiinter.tsv
   cohort.d<threshold>.population_count_quantized.bed

VCF mode keeps the uncompressed population-count BED in the work directory when
``--keep-work`` is set.
