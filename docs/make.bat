@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation.

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure Sphinx is installed,
	echo.then set the SPHINXBUILD environment variable to point to the full path
	echo.of the 'sphinx-build' executable. Alternatively, add the directory with
	echo.'sphinx-build' to PATH.
	echo.
	echo.If you do not have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
popd
