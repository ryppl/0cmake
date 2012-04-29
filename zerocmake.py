from zeroinstall.injector import cli
from subprocess import check_call
import sys
import argparse
from os import environ
import tempfile
import shutil

def _0launch(args, **kw):
    print '0cmake: 0launch '+' '.join(repr(x) for x in args)
    if not kw.get('noreturn'):
        # Run 0launch in a subprocess so we get control back
        # afterwards.  Otherwise the 0launch process *replaces* itself
        # with the process being launched (on posix).
        check_call(
            [sys.executable
             , '-c', 'import sys\n'
                     'from zeroinstall.injector import cli\n'
                     'cli.main(sys.argv[1:])\n']
            + list(args))
    else:
        # The caller has told us he doesn't need to regain control, so
        # launch the command directly.
        cli.main(args)

def cmake(args, **kw):
    _0launch(['--not-before=2.8.8', 'http://ryppl.github.com/feeds/cmake.xml'] + args, **kw)

def run(args):

    if args.overlay:
        SRCDIR = tempfile.mkdtemp()
    else:
        SRCDIR = args.source

    try:
        if args.overlay:
            print '0cmake: preparing source directory with overlay...'
            cmake(['-E', 'copy_directory', args.source, SRCDIR])
            cmake(['-E', 'copy_directory', args.overlay, SRCDIR])


        print '0cmake: configuring...'
        cmake([
                '-DCMAKE_MODULE_PATH='+args.cmake_module_path
              , '-DBUILD_TYPE='+ ('Debug' if args.component == 'dbg' else 'Release')
              ]
            + ([] if args.component == 'doc' else [ '-DRYPPL_DISABLE_DOCS=1' ])
            + [ '-DRYPPL_DISABLE_TESTS=1', '-DRYPPL_DISABLE_EXAMPLES=1' ]
            + [ SRCDIR ])

        print '0cmake: building...'
        cmake(
              ['--build', '.']
            + {'doc':['--target','documentation']}.get(args.component,[]) )

        print '0cmake: installing...'
        cmake(
              ['-DCOMPONENT='+args.component]
            + ['-DCMAKE_INSTALL_PREFIX='+args.prefix, '-P', 'cmake_install.cmake']
            , noreturn=args.overlay is None)

    except:
        if args.overlay:
            shutil.rmtree(SRCDIR, ignore_errors=True)
        raise

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
