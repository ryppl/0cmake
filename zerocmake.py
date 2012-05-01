from zeroinstall.injector import cli
from subprocess import check_call
import sys
import argparse
from os import environ as env
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
    use_overlay = args.build_type in ('headers','preinstall','dbg')
    component = {
        'headers':'dev', 'preinstall':'dev'
        }.get(args.build_type) or args.build_type

    if use_overlay:
        SRCDIR = tempfile.mkdtemp()
    else:
        SRCDIR = env['SRCDIR']

    try:
        if use_overlay:
            print '0cmake: preparing source directory with overlay...'
            cmake(['-E', 'copy_directory', env['SRCDIR'], SRCDIR])
            cmake(['-E', 'copy_directory', env['BOOST_CMAKELISTS_OVERLAY'], SRCDIR])


        print '0cmake: configuring...'
        cmake([
                '-DCMAKE_MODULE_PATH=' + env['RYPPL_CMAKE_MODULE_PATH']
              , '-DCMAKE_BUILD_TYPE='+ ('Debug' if component == 'dbg' else 'Release')
              ]
            + ([] if component == 'doc' else [ '-DRYPPL_DISABLE_DOCS=1' ])
            + [ '-DRYPPL_DISABLE_TESTS=1', '-DRYPPL_DISABLE_EXAMPLES=1' ]
            + [ SRCDIR ])

        print '0cmake: building...'
        cmake(
              ['--build', '.']
            + {'doc':['--target','documentation']}.get(component,[]) )

        print '0cmake: installing...'
        cmake(
              ['-DCOMPONENT='+component]
            + ['-DCMAKE_INSTALL_PREFIX='+env['DISTDIR'], '-P', 'cmake_install.cmake']
            , noreturn=not use_overlay)

    except:
        if use_overlay:
            shutil.rmtree(SRCDIR, ignore_errors=True)
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='0compile utility for CMake-based Ryppl projects')

    parser.add_argument(
        'build_type'
      , choices=('headers','bin','dev','doc','dbg','preinstall')
      , help='Determines the type of build/install step to perform')

    run(parser.parse_args())
