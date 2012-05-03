from zeroinstall.injector import cli
from subprocess import check_call
import sys
import argparse
from os import environ as env
import tempfile
import shutil
import os

def _msg(*args):
    print '0cmake:',
    for x in args:
        print x,
    print
    sys.stdout.flush()

def _0launch(args, **kw):
    _msg('0launch '+' '.join(repr(x) for x in args))
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
    use_overlay = args.build_type in ('headers','preinstall','cluster','dbg')
    component = 'dev' if args.build_type in ('headers','preinstall','cluster') else args.build_type

    if use_overlay:
        SRCDIR = os.path.join(os.getcwd(),'ryppl_overlay')
    else:
        SRCDIR = env['SRCDIR']

    if args.build_type in ('preinstall', 'cluster'):
        # since we actually want to save the built state in the cache,
        # use the DISTDIR to do the build.
        os.chdir(env['DISTDIR'])

    if use_overlay:
        _msg('preparing source directory with CMakeLists.txt overlays...')

        if args.cluster:
            # Copy each individual member of the cluster into a subdirectory of SRCDIR
            cluster = [x.split('=',1) for x in args.cluster]
            for package,subdir in cluster:
                cmake(['-E', 'copy_directory', env[package + '_SRCDIR'], os.path.join(SRCDIR,subdir)])

            _msg('cluster',cluster)
            # Build the CmakeLists.txt file that includes them all
            open(os.path.join(SRCDIR,'CMakeLists.txt'), 'w').write(
                'cmake_minimum_required(VERSION 2.8.8 FATAL_ERROR)\n'
                + '\n'.join('add_subdirectory('+x+')' for _,x in cluster)
                )
        else:
            cmake(['-E', 'copy_directory', env['SRCDIR'], SRCDIR])

        cmake(['-E', 'copy_directory', env['BOOST_CMAKELISTS_OVERLAY'], SRCDIR])


    _msg('configuring...')
    config_args = ['-DCMAKE_VERBOSE_MAKEFILE=1',
            '-DCMAKE_MODULE_PATH=' + env['RYPPL_CMAKE_MODULE_PATH']
          , '-DCMAKE_BUILD_TYPE='+ ('Debug' if component == 'dbg' else 'Release')
          , '-DRYPPL_DISABLE_TESTS=1', '-DRYPPL_DISABLE_EXAMPLES=1'
          ]

    if component != 'doc':
        config_args.append( '-DRYPPL_DISABLE_DOCS=1')

    config_args.append(SRCDIR)
    cmake(['-DRYPPL_INITIAL_PASS=1']+config_args)

    if args.build_type in ('preinstall','cluster'):
        _msg('2nd configuration pass...')
        cmake(['-DRYPPL_INITIAL_PASS=0']+config_args)

    _msg('building...')
    cmake(
          ['--build', '.']
        + {'doc':['--target','documentation']}.get(component,[]) )

    if args.build_type in ('preinstall','cluster'):
        _msg('adjusting installation scripts...')
        script_name = 'cmake_install.cmake'
        for root, dirnames, filenames in os.walk('.'):
            if script_name in filenames:
                script_path = os.path.join(root, script_name)
                old_script = open(script_path).read()

                build_dir = os.getcwd() + '/'

                assert build_dir in old_script or root != '.' \
                    , "Couldn't find %s in %s:\n" % (build_dir, script_path) + old_script

                new_script = old_script.replace(build_dir, '${RYPPL_PREINSTALL_DIR}/')
                open(script_name,'w').write(new_script)
    else:
        _msg('installing...')
        cmake(
              ['-DCOMPONENT='+component]
            + ['-DCMAKE_INSTALL_PREFIX='+env['DISTDIR'], '-P', 'cmake_install.cmake']
            , noreturn=not use_overlay)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='0compile utility for CMake-based Ryppl projects')

    parser.add_argument(
        'build_type'
      , choices=('headers','bin','dev','doc','dbg','preinstall','cluster')
      , help='Determines the type of build/install step to perform')

    parser.add_argument(
        'cluster'
      , nargs='*'
      , help='The elements of the cluster')

    run(parser.parse_args())
