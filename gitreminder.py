#!/usr/bin/env python
# encoding=utf-8
#

####### utility functions
class GitReminderUtils(object):
    @classmethod
    def import_module(cls, module, doc_url):
        if not cls.try_import_module(module):
            cls.warn_missing_module(module, doc_url)
            return False
        return True
    @staticmethod
    def warn_missing_module(module, doc_url):
        print "WARNING: module [%s] not found. Please install it first. Info: %s" % (module, doc_url)
    @staticmethod
    def try_import_module(module):
        try:
            globals()[module] = __import__(module)
            return globals()[module]
        except ImportError:
            return None

####### imports and module checks and some constants
EXIT_ERROR_GENERAL_ERROR  = 2
EXIT_ERROR_MODULE_MISSING = 3

import os, sys, datetime, codecs, re, traceback

imported  = True
imported &= GitReminderUtils.import_module("argparse", "http://docs.python.org/2/library/argparse.html#module-argparse")
imported &= GitReminderUtils.import_module("git", "http://packages.python.org/GitPython/")
imported &= GitReminderUtils.import_module("colorama", "http://pypi.python.org/pypi/colorama")
imported &= GitReminderUtils.import_module("blessings", "http://pypi.python.org/pypi/blessings/")

if __name__ == "__main__":
    if not imported:
        print "One ore more modules are missing. Please install them first."
        sys.exit(EXIT_ERROR_MODULE_MISSING)
else:  #in case we are used within a script or in a shell, but not directly as script
    if not imported: raise Exception("One ore more modules are missing. Please install them first.")

####### initialization for some things
#initalize some terminal/commandline goodness
colorama.init() #make this colorful terminal power available in Windows as well
term = blessings.Terminal()

def p(s):
    try:
        print (u"%s{t.normal}" % unicode(s)).format(t=term)
    except:
        print "!!!!!!!!ERROR PRINTING!!!!! ", type(s), s
        print (u"%s{t.normal}" % str(s)).format(t=term)
def pdim(s):
    p(term.dim + unicode(s))

####### CONSTANTS & globals

CURRENT_PATH  = os.path.dirname(os.path.abspath(__file__))

VERBOSITY_SILENT        = 0
VERBOSITY_WHISPERING    = 1
VERBOSITY_NORMAL        = 2
VERBOSITY_NOISY         = 3
VERBOSITY               = VERBOSITY_SILENT #is overwritten later, but should default to silent
def vvv_is_silent():
    return VERBOSITY == VERBOSITY_SILENT
def vvv_ge_whisper():
    return VERBOSITY >= VERBOSITY_WHISPERING
def vvv_is_whisper():
    return VERBOSITY == VERBOSITY_WHISPERING
def vvv_ge_normal():
    return VERBOSITY >= VERBOSITY_NORMAL
def vvv_is_normal():
    return VERBOSITY == VERBOSITY_NORMAL
def vvv_is_noisy():
    return VERBOSITY == VERBOSITY_NOISY

####### git functions

class GitReminderGit(object):

    @classmethod
    def check_repositories(cls, path_for_repositories, args=None):
        gits, gits_remotes, gits_dirty, gits_may_need_push, gits_detached = [], [], [], [], []
        if vvv_ge_normal(): pdim("Checking if any repositories are marked dirty or need to be pushed.")
        if path_for_repositories is None or len(path_for_repositories) == 0:
            if vvv_ge_whisper(): p("{t.bold_red}No repositories to work with.".format(t=term))
            return (gits, gits_remotes, gits_dirty, gits_may_need_push, gits_detached)
        for repository_path in path_for_repositories:
            if vvv_is_normal(): p("Checking [{t.green}%s{t.normal}] ...".format(t=term) % (repository_path))
            repository = cls.check_repository(repository_path, args=args)
            if repository is not None:
                gits.append(repository)
                remote_branch, remote_name, remote_ref = cls.get_remote_branch(repository, args=args)
                gits_remotes.append(remote_branch)
                if repository.bare:
                    #bare repositories: should we even return them in the gits list?
                    if vvv_ge_normal(): p("Bare repository ignored: {t.red}%s" % repository_path)
                    continue
                is_dirty = repository.is_dirty()
                if vvv_is_noisy():
                    pdim("[{t.green}%s{t.normal}] is dirty? {t.yellow}%s".format(t=term) % (repository_path, is_dirty))
                if is_dirty:
                    gits_dirty.append(repository)
                elif repository.head.is_detached:
                    if vvv_ge_normal(): p("{t.red}Detached head{t.normal} in repository: {t.green}%s" % repository.working_dir)
                    gits_detached.append(repository)
                elif cls.has_valid_branch(repository, args=args):
                    gits_may_need_push.append(repository)
            else:
                if vvv_is_noisy(): p("{t.bold_red}Not a valid repository!")
        return (gits, gits_remotes, gits_dirty, gits_may_need_push, gits_detached)

    @classmethod
    def check_repository(cls, path_to_repository, args=None):
        try:
            return git.Repo(path_to_repository)
        except Exception, ex:
            if vvv_ge_normal():
                p(u"{t.bold_red}Error{t.normal}: repository [{t.red}%s{.t.normal}] could not be read. Reason: %s" %
                  (path_to_repository, unicode(ex)))
            return None
    @staticmethod
    def has_valid_branch(repo, args=None):
        if repo.is_dirty():
            if vvv_ge_normal(): p(u"Repository is {t.red}dirty{t.normal}.")
            return False
        if repo.head.is_detached:
            if vvv_ge_normal(): p(u"{t.red}Detached head{t.normal} in repository: {t.green}%s" % repo.working_dir)
            return False
        branch = repo.active_branch#TODO: we should really check all branches, not only the active one
        return branch.is_valid()

    @staticmethod
    def get_remote_branch(repo, args=None, force_silence=False):
        try:
            if repo.head.is_detached:
                if not force_silence: p(u"{t.red}Detached head{t.normal} in repository: {t.green}%s" % repo.working_dir)
                return (None, None, None)
            local_branch = repo.active_branch
            lname = local_branch.name #eg: master
            active_remote = repo.remote()
            arname = active_remote.name #eg: origin
            for remote_branch in repo.remotes:
                rbname = remote_branch.name #eg: origin
                if vvv_ge_normal():
                    if not force_silence: p(u"Checking remote [{t.yellow}%s{t.normal}] for branch [{t.green}%s{t.normal}]" % (arname, lname))
                if arname != rbname: continue
                for ref in remote_branch.refs:
                    rhead = ref.remote_head #eg: master
                    rname = ref.remote_name #eg: origin
                    rr    = ref.name        #eg: origin/master
                    if rname == arname and lname == rhead:
                        if vvv_is_noisy():
                            if not force_silence: p(u"Found [{t.yellow}%s{t.normal}] on [{t.green}%s{t.normal}] for: {t.cyan}%s" % (lname, rname, repo.working_dir))
                        return (active_remote, rr, ref)
            return (None, None, None)
        except Exception, ex:
            if not force_silence: p(u"{t.bold_red}ERROR: %s" % (unicode(ex)))
            return (None, None, None)

    @staticmethod
    def can_be_pushed_to_remote(repo, args=None, remote_branch=None, remote_name=None, remote_ref=None):
        if remote_branch is None:
            remote_branch, remote_name, remote_ref = GitReminderGit.get_remote_branch(repo, args=args, force_silence=True)
        if remote_branch is None:
            if vvv_ge_normal(): p(u"{t.red}No remote repository found{t.normal} for: {t.green}%s" % repo.working_dir)
            return False, None, None
        #check if the latest local commit is available in the remote repo, if not, we could push the local one
        #TODO: this should be improved. Right now it is a simple comparision of the last commit in a remote branch and
        #      last commit in the local one, BUT the remote might already be moved forward by other devs, so the last
        #      commit is not necessarily the same. The last local commit might also be included in the remote
        #      repository/branch. In that case this comparision here will fail.
        try:
            rsha = remote_ref.commit.hexsha
            #p(u"RSHA: %s " % rsha)
            lsha = repo.active_branch.commit.hexsha
            #p(u"LSHA: %s " % lsha)
            return rsha != lsha, lsha, rsha
        except Exception, ex:
            p(u"{t.bold_red}Warning:{t.normal} could not determine SHA commit hashes for remote and/or local branch for repository: {t.green}%s" % repo.working_dir)
            p(u"{t.bold_red}%s" % unicode(ex))
        return False, None, None

####### ssh/sftp/scp functions



####### zip/tar functions



####### Command line handling
class GitReminderCmdline(object):
    @classmethod
    def get_git_repositories(cls, paths, args=None):
        gits = []
        for path in paths:
            gits += cls._gather_git_repositories(path, args=args)
        gits_count = len(gits)
        if gits_count == 0:
            p(term.red + "No repositories found in the given path(s).")
            return False
        s = "repository" if gits_count == 1 else "repositories"
        p(u"Found [{t.bold_green}%d{t.normal}] git %s." % (len(gits), s))
        return gits

    @staticmethod
    def _gather_git_repositories(path, args=None):
        gits, i = [], 0
        if vvv_ge_normal(): pdim("Searching for git repositories in %s" % path)

        for root, folders, files in os.walk(path):
            i += 1
            if vvv_is_noisy(): pdim("{t.green}%d{t.yellow}: {t.italic}%s{t.no_italic}..." % (i, root))
            if i % 400 == 0 and vvv_is_normal() and not vvv_is_noisy(): pdim("Still scanning, found so far [{t.green}%d{t.normal}{t.dim}]" % (len(gits)))
            if '.svn' in folders:
                folders.remove('.svn')
            if '.git' in folders:
                # don't go into any .git directories.
                folders.remove('.git')
                gits.append(root)
                if vvv_ge_whisper(): p("{t.green}Repository{t.normal}: {t.yellow}{t.italic}%s{t.no_italic}" % (root))

        if vvv_ge_normal():
            p("Found [{t.green}%d{t.normal}] repositories in {t.green}%s" % (len(gits), path))
        return gits

if __name__ == "__main__":
    try:
        #define command line arguments, evalute them and then run the magic voodoo codes
        parser = argparse.ArgumentParser(description="""Scan a directory for git repositories and check if they are
                                                        dirty and/or need to be pushed.""",
                                        epilog="Use the source.")
        parser.add_argument('--path', '-p', action='append', help="The path which should be scanned for git repositories. May be defined more than once for multiple locations.")
        parser.add_argument('--verbose', '-v', action='count', help="Verbosity level. Default is sparse verbosity. -v would be a bit more talkative, -vv is informative, -vvv is chatty.")
        args = parser.parse_args()
        VERBOSITY = args.verbose or VERBOSITY_SILENT
        paths = args.path or []
        if len(paths) == 0:
            paths.append(os.getcwd())
            p("No --path specified (see --help for information). Using the current directory instead: {t.bold}" + paths[0])

        repos = GitReminderCmdline.get_git_repositories(paths, args=args)
        gits, gits_remotes, gits_dirty, gits_may_need_push, gits_detached = GitReminderGit.check_repositories(repos, args=args)
        p("""Repositories checked: {t.green}%d{t.normal}; valid: {t.green}%d{t.normal}; dirty: {t.green}%d{t.normal}; may need push: {t.green}%d{t.normal}; detached: {t.green}%d{t.normal};""" %
          (len(repos), len(gits), len(gits_dirty), len(gits_may_need_push), len(gits_detached)))

        for repo in gits_detached:
            p("{t.yellow}Detached HEAD{t.normal} in repository: {t.green}%s" % (repo.working_dir))
        for repo in gits_dirty:
            p("{t.yellow}Dirty{t.normal} repository: {t.green}%s" % (repo.working_dir))
        for repo in gits_may_need_push:#TODO: we should really check all branches, not only the active one
            remote_branch, remote_name, remote_ref = GitReminderGit.get_remote_branch(repo, force_silence=True)
            can_push, lsha, rsha = GitReminderGit.can_be_pushed_to_remote(repo, args=args, remote_branch=remote_branch, remote_name=remote_name, remote_ref=remote_ref)
            if can_push:
                if vvv_ge_normal():
                    p("Repository {t.magenta}can be pushed{t.normal} to [{t.cyan}%s{t.normal}]: LSHA [{t.yellow}%s{t.normal}] RSHA [{t.cyan}%s{t.normal}] {t.green}%s" % (remote_name, lsha, rsha, repo.working_dir))
                else:
                    p("Repository {t.magenta}can be pushed{t.normal} to [{t.cyan}%s{t.normal}]: {t.green}%s" % (remote_name, repo.working_dir))

        sys.exit(0)
    except Exception, ex:
        tb = traceback.format_exc()
        print u"ERROR! There was an error.\n\n%s\n%s" % (unicode(ex), unicode(tb))
        sys.exit(EXIT_ERROR_GENERAL_ERROR)
