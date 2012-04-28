from zeroinstall.injector import cli
from multiprocessing import Process
import sys
import argparse
from os import environ
import tempfile
import shutil

def _0launch(args, **kw):
    if not kw.get('noreturn'):
        # Because on *nix, the 0launch process replaces itself with
        # the process being launched, if we need to get control back,
        # we must run 0launch in a subprocess.
        p = Process(target = cli.main, args=(args,))
        p.start()
        p.join()
        if p.exitcode:
            exit(p.exitcode)
    else:
        # The caller has told us he doesn't need to regain control, so
        # launch this command directly.
        cli.main(args)
    
def cmake(args, **kw):
    _0launch(['--not-before=2.8.8', 'http://afb.users.sourceforge.net/zero-install/interfaces/cmake.xml'] + args, **kw)

def run(args):

    if args.overlay:
        SRCDIR = tempfile.mkdtemp()
    else:
        SRCDIR = args.source

    try:
        if args.overlay:
            cmake(['-E', 'copy_directory', args.source, SRCDIR])
            cmake(['-E', 'copy_directory', args.overlay, SRCDIR])

        
        common_args = (
            '-DCMAKE_MODULE_PATH='+args.cmake_module_path
          , '-DCOMPONENT='+args.component
          , '-DRYPPL_DISABLE_TESTS=1'
          , '-DRYPPL_DISABLE_EXAMPLES=1')

        if args.component != 'doc':
            common_args += ('-DRYPPL_DISABLE_DOCS=1',)

        # configure
        cmake(
            common_args
            + {'dbg':['-DBUILD_TYPE=Debug '], 'bin':['-DBUILD_TYPE=Release ']}.get(args.component, [])
            + [ './source' ])

        # build
        cmake(
            common_args
            + ['--build .'] 
            + {'doc':['--target','documentation']}.get(args.component,[]) )

        # install
        cmake(
            common_args
            + ['-DCMAKE_INSTALL_PREFIX='+args.prefix, '-P', 'cmake_install.cmake']
            , noreturn=args.overlay is None)

    except:
        if args.overlay:
            shutil.rmtree(SRCDIR, ignore_errors=True)

def envvar(name):
    return '%'+name+'%' if sys.platform == 'windows' else '${'+name+'}'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='0compile utility for CMake-based Ryppl projects')

    parser.add_argument(
        '--component'
      , choices=['dev','bin','doc','dbg']
      , required=True
      , help='the CMake component to be built')

    parser.add_argument(
        '--source'
      , default=environ['SRCDIR']
      , help='The directory of the package source.  Defaults to '+envvar('SRCDIR'))

    parser.add_argument(
        '--prefix'
      , default=environ['DISTDIR']
      , help='The installation directory.  Defaults to '+envvar('DISTDIR'))

    parser.add_argument(
        '--overlay'
      , help='A directory to be overlaid on the source directory before building')

    parser.add_argument(
        '--cmake-module-path'
      , default=environ['RYPPL_CMAKE_MODULE_PATH']
      , help='Passed to CMake as CMAKE_MODULE_PATH.  Defaults to '+envvar('RYPPL_CMAKE_MODULE_PATH'))

    run(parser.parse_args())
