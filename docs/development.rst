Development
***********

Set up a development environment
================================

.. code-block:: console

   mamba env create -f environment.yml
   conda activate wisp
   python -m pip install -e ".[dev,docs]"

Run checks
==========

.. code-block:: console

   ruff check .
   mypy
   pytest
   python -m build

Build documentation
===================

.. code-block:: console

   make -C docs html

Treat Sphinx warnings as issues during local development:

.. code-block:: console

   sphinx-build -W -b html docs docs/_build/html

Project layout
==============

.. code-block:: text

   src/wisp_mask/     package source
   tests/               unit and workflow tests
   tests/test_data/     small 1000 Genomes fixtures and download scripts
   docs/                Sphinx documentation

Implementation overview
=======================

The public CLI is defined in ``wisp_mask.cli``. Parsed arguments are converted
to ``RunConfig`` and passed to ``run_workflow``. The workflow validates the input
mode, runs either the BAM/CRAM or VCF builder, writes ``wisp.bed.gz``,
and creates the tabix index.
