"""
xcpy - interfaces with external programs from within Bruker-TopSpin

USAGE
xcpy
xcpy [OPTIONS]
xcpy [OPTIONS] [SCRIPTNAME]

INSTALLATION
1. Copy (or symlink) this file to the following directory:
<topspin_location>/exp/stan/nmr/py/user/
2. If you now type 'xcpy' on the command line within Topspin,
this documentation should pop up
3. A configuration file needs to be written out so that xcpy
knows the location of the CPython executable and a folder where
the .py scripts are located. This can be done by 'xcpy -s'. This
can be rewritten at any time point using the same command.


DESCRIPTION
xcpy supports running external scripts via Jython (subprocess module)
that ships with Topspin. Currently, it allows only external CPython
programs to run. By default, it passes the current folder, expno and procno
to the external CPython program (if available).


OPTIONS
-h, --help: Brings up this docstring. Also brings it up when no other
\toption is given.

-s, --settings: Opens a dialog to write out a configuration file. The
\tlocation of the Cpython executable and the folder where all scripts
\tare located can be given. Use full path names for this, i.e., use
\t'/usr/bin/python3' for *nix instead of 'python3' or '~/folder/python3',
\tand 'C:\python.exe' for Windows (note the .exe) extension. If the
\tconfiguration file already exists, the entries will be verified and
\tthe dialog will be populated with them if these are found to be correct.
\tElse, an error message with the configuration file will be returned and
\tthe dialogs will be kept empty.

-n, --name: Opens a dialog box to give the path of a script to be run

-c, --config: Prints contents of the configuration file, if it exists.
\tIf no configuration file is found, it prints 'None'

-d, --dry-run: Prints out the command that will be executed by the subprocess
\tmodule if this option is not given.

--no-args: Does not pass any arguments (current data folder, etc) to
\tthe external program

--use-shell: Uses shell to run the subprocess command. By default, this is
\tnot used for *nix, but is used for Windows. [Warning: this is a known
\tsecurity risk and users are advised to be careful with their input]

"""
import sys
import os
from subprocess import Popen, PIPE, STDOUT

try:
    from ConfigParser import SafeConfigParser
except ModuleNotFoundError:
    # this will only fail if Python 3 is used
    # but that error willl be handled by the
    # check_jython() function
    pass


def topspin_error():
    errmsg = """
    This file is meant to be executed
    using Jython from within Topspin
    Please see the doctring for more
    details.
    """
    return errmsg


def check_jython():
    """
    Checks whether Jython is being used to run this script
    from within Topspin

    """
    # some of the functions defined in the global namespace
    # by Topspin which are also used by xcpy
    topspin_inbuilts = ["MSG", "INPUT_DIALOG", "CURDATA"]

    g = globals().keys()
    for function in topspin_inbuilts:
        if function in g:
            pass
        else:
            raise Exception(topspin_error())
    return True


def topspin_location():
    """
    Gets Topspin home directory. Also serves to check
    whether the script is being executed from within
    Topspin or externally.

    """
    try:
        # topspin >= 3.6
        toppath = sys.getBaseProperties()["XWINNMRHOME"]
    except AttributeError:
        try:
            # topspin >= 3.1 and <= 3.5
            toppath = sys.registry["XWINNMRHOME"]
        except (AttributeError, KeyError):
            # topspin < 3.1
            toppath = sys.getEnviron()["XWINNMRHOME"]

    # if all the above fail, there should be an exception raised and
    # the function should not return anything
    return toppath


def read_cfg(filename):
    """
    Reads in the configuration file

    """
    config = SafeConfigParser()
    config.read(filename)

    try:
        cpyname = config.get("xcpy", "cpython")
    except (NoSectionError, NoOptionerror, KeyError):
        cpyname = ""

    try:
        scripts_location = config.get("xcpy", "scripts_location")
    except (NoSectionError, NoOptionerror, KeyError):
        scripts_location = ""

    if cpyname:
        verify_python(cpyname)

    if scripts_location:
        exists(scripts_location, raise_error=True)

    return cpyname, scripts_location


def write_cfg(outfile, infile=None):
    """
    Writes or overwrites a configuration file

    """
    if infile is not None:
        try:
            cpyname, scripts_location = read_cfg(infile)
        except Exception:
            if exists(infile):
                errmsg = """
                    The following configuration was found in the file {}:

                    {}

                    These settings are likely incorrect.
                    you can enter the correct settings at the next dialog box.
                    Press 'Close' to continue.
                    """.format(
                    infile, show_config(infile, printing=False)
                )
                MSG(errmsg)
            cpyname, scripts_location = "", ""
    else:
        cpyname, scripts_location = "", ""

    cpyname, scripts_location = INPUT_DIALOG(
        "XCPy Configuration",
        "Please Click on OK to write this configuration.",
        ["CPython Executable", "CPython Scripts Location"],
        [cpyname, scripts_location],
        ["", ""],
        ["1", "1"],
    )

    if not cpyname or not scripts_location:
        MSG("Invalid configartion specified. Config file not written")
    else:
        config = SafeConfigParser()
        config.add_section("xcpy")
        config.set("xcpy", "cpython", cpyname)
        config.set("xcpy", "scripts_location", scripts_location)

        with open(outfile, "w") as f:
            config.write(f)
        MSG("Written Configuration file at: " + outfile)


def exists(filename, raise_error=False):
    """
    Checks whether a file exists either returns False or
    raises an exception

    """
    if os.path.exists(filename):
        return True
    elif raise_error:
        raise Exception("{} not found".format(filename))
    else:
        return False


def current_data():
    """
    Returns the current EXPNO and PROCNO open in Topspin,
    if executed when a data folder is open

    """
    cd = CURDATA()

    if cd is not None:
        current_dir = os.path.join(cd[3], cd[0])
        current_expno = cd[1]
        current_procno = cd[2]
        return [current_dir, current_expno, current_procno]

    else:
        MSG(
            """No data folder seems to be open!
            No arguments will be passed on. If this is intentional,
            you should run the command with the --no-args option
            which will get rid of this message"""
        )
        return []


def get_scriptname():
    """
    Opens up a dialog box to get the script name

    """
    scriptname = INPUT_DIALOG(
        "Script",
        "Type the full path and name of the script to be run",
        ["CPython Script"],
        [""],
        [""],
        ["1"],
    )

    return scriptname


def run(cpython, script, pass_current_folder=True, use_shell=None, dry=None):
    """
    Runs a cpython script

    """
    if pass_current_folder is True:
        cd = current_data()
    else:
        cd = []

    if use_shell is None:
        if os.name == "nt":
            use_shell = True
        else:
            use_shell = False

    args = [cpython, script] + cd

    if dry:
        MSG("The following command will be executed: \n" + " ".join(args))
        process = None

    else:
        process = Popen(
            args, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=use_shell
        )
        process.stdin.close()

    return process


def verify_completion(process):
    """
    Verify that the output is correct
    """

    if process is not None:
        errmsg = [line for line in iter(process.stdout.readline, "")]

        if not errmsg:
            MSG("Script executed to completion")
        else:
            MSG("".join(errmsg))

    else:
        return


def verify_python(command):
    """
    Verify that the command to be saved in the config file points
    to a valid python executable. This is a rudimentary check!

    """
    if not os.path.exists(command):
        raise OSError("The command {} does not seem to exist".format(command))

    command = command.split(os.sep)[-1]
    if command.lower().find("python") != 0:

        errmsg = """
            {} does not seem to be a valid python file.
            Please check the configuration file using 'xcpy --config',
            or change the congiguration file using 'xcpy --settings'
            This attempt will be aborted.
            """.format(
            command
        )

        raise OSError(errmsg)


def show_config(filename, printing=True):
    """
    Shows the configuration file if present

    """
    try:
        with open(filename, "r") as f:
            config = f.read()
            if printing:
                MSG(config)
    except FileNotFoundError:
        if printing:
            MSG(filename + " not found")
        config = None

    return config


def main():

    # check if the program is running via topspin
    # and get the path of topspin
    if check_jython():
        toppath = topspin_location()

    # path and name of the configuration file is hard-coded
    config_file = os.path.join(
        toppath, "exp", "stan", "nmr", "py", "user", "xcpy.cfg"
    )

    # get arguments passed to xcpy
    argv = sys.argv
    if len(argv) == 1:
        argv.append("--help")

    # Case: return docstring
    if argv[1] in ["-h", "--help"]:
        if len(argv) > 2:
            MSG("Opening Documentation. All other options ignored. Press OK")
        MSG(__doc__)

    # check if configuration exists
    elif not os.path.exists(config_file):
        MSG(
            """
            Configuration file does not exist.
            An input box will be opened next to write it.
            Alternately, it can be manually edited at {}.
            Press 'Close' to continue.
            """.format(
                config_file
            )
        )
        write_cfg(config_file)

    # if configuration settings are to be changed
    elif argv[1] in ["-s", "--settings"]:
        if len(argv) > 2:
            MSG("Opening configuration settings. Ignored all other options")
        write_cfg(config_file, config_file)

    # show configuration
    elif argv[1] in ["-c", "--config"]:
        show_config(config_file)

    else:
        if "--use-shell" in argv:
            use_shell = True
        else:
            use_shell = False

        if "--no-args" in argv:
            pass_current_folder = False
        else:
            pass_current_folder = True

        if "--dry-run" in argv or "-d" in argv:
            dry = True
        else:
            dry = False

        # read configuration
        cpyname, folder = read_cfg(config_file)

        if "-n" in argv or "--name" in argv:
            scriptname = get_scriptname()
        else:
            # see if script is there and then run
            scriptname = os.path.join(folder, argv[-1])

        if exists(scriptname):
            process = run(
                cpyname, scriptname, pass_current_folder, use_shell, dry
            )
        else:
            scriptname = scriptname + ".py"
            if exists(scriptname, raise_error=True):
                process = run(
                    cpyname, scriptname, pass_current_folder, use_shell, dry
                )

        # handle errors and print messages from cpython
        verify_completion(process)


if __name__ == "__main__":
    main()
