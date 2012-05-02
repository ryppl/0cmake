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
    use_overlay = args.build_type in ('headers','preinstall','dbg')
    component = 'dev' if args.build_type in ('headers','preinstall') else args.build_type

    if args.build_type == 'preinstall':
        # since we actually want to save the built state in the cache,
        # use the DISTDIR to do the build.
        os.chdir(env['DISTDIR'])

    if use_overlay:
        SRCDIR = tempfile.mkdtemp()
    else:
        SRCDIR = env['SRCDIR']

    try:
        if use_overlay:
            _msg('preparing source directory with overlay...')
            cmake(['-E', 'copy_directory', env['SRCDIR'], SRCDIR])
            cmake(['-E', 'copy_directory', env['BOOST_CMAKELISTS_OVERLAY'], SRCDIR])


        _msg('configuring...')
        config_args = [
                '-DCMAKE_MODULE_PATH=' + env['RYPPL_CMAKE_MODULE_PATH']
              , '-DCMAKE_BUILD_TYPE='+ ('Debug' if component == 'dbg' else 'Release')
              , '-DRYPPL_DISABLE_TESTS=1', '-DRYPPL_DISABLE_EXAMPLES=1'
              ]

        if component != 'doc':
            config_args.append( '-DRYPPL_DISABLE_DOCS=1')

        config_args.append(SRCDIR)
        cmake(config_args)

        if args.build_type == 'preinstall':
            _msg('2nd configuration pass...')
            cmake(config_args)

        _msg('building...')
        cmake(
              ['--build', '.']
            + {'doc':['--target','documentation']}.get(component,[]) )

        if args.build_type == 'preinstall':
            _msg('adjusting installation scripts...')
            script_name = 'cmake_install.cmake'
            for root, dirnames, filenames in os.walk('.'):
                if script_name in filenames:
                    script_path = os.path.join(root, script_name)
                    old_script = open(script_path).read()
                    
                    assert build_dir in old_script, "Couldn't find %s in %s:\n" % (
                        build_dir, script_path, old_script)

                    build_dir = os.getcwd() + '/'
                    
                    new_script = old_script.replace(build_dir, '${RYPPL_PREINSTALL_DIR}/')
                    open(script_name,'w').write(new_script)
        else:
            _msg('installing...')
            cmake(
                  ['-DCOMPONENT='+component]
                + ['-DCMAKE_INSTALL_PREFIX='+env['DISTDIR'], '-P', 'cmake_install.cmake']
                , noreturn=not use_overlay)

    except:
        if use_overlay:
            _msg('cleaning up temporary source directory...')
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
