Installation
************

Requirements
============

``sprite`` requires Python 3.11 or 3.12. Runtime command line tools depend
on the input mode:

* BAM/CRAM mode requires ``samtools``, ``mosdepth``, ``bedtools``, ``bgzip``, and ``tabix``.
* All-sites VCF mode requires ``bgzip`` and ``tabix``.

The repository environment file installs these external tools from conda-forge
and bioconda.

Conda environment
=================

From the repository root, create and activate the development environment:

.. code-block:: console

   mamba env create -f environment.yml
   conda activate sprite
   python -m pip install -e ".[dev]"

If the environment already exists, update it instead:

.. code-block:: console

   mamba env update -n sprite -f environment.yml
   conda activate sprite
   python -m pip install -e ".[dev]"

Verify the CLI
==============

After installation, verify the ``sprite`` command:

.. code-block:: console

   sprite --help
   sprite --version

Build these docs locally
========================

Install the docs dependencies and build the HTML documentation:

.. code-block:: console

   python -m pip install -e ".[docs]"
   make -C docs html

The rendered site is written to ``docs/_build/html/index.html``.
