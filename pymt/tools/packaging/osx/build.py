import os, sys, shutil, shlex, re
from urllib.request import urlretrieve
from subprocess import Popen, PIPE
from distutils.cmd import Command





class OSXPortableBuild(Command):
    description = "custom build command that builds portable osx package"
    user_options = [
        ('dist-dir=', None,
         "path of dist directory to use for building portable pymt, the resulting disk image will be output to this driectory. defaults to cwd."),
        ('deps-url=', None,
         "url of binary dependancies for portable pymt package default: http://pymt.googlecode.com/files/portable-deps-osx.zip"),
        ('no-cext', None,
         "flag to disable building of c extensions")
    ]

    def initialize_options(self):
        self.dist_dir = None
        self.deps_url = None
        self.no_cext = None

    def finalize_options(self):
        if not self.deps_url:
            self.deps_url = 'http://pymt.googlecode.com/files/portable-deps-osx.zip'
        if not self.dist_dir:
            self.dist_dir =  os.getcwd()

        self.src_dir = os.path.dirname(sys.modules['__main__'].__file__)
        self.dist_name = self.distribution.get_fullname() # e.g. PyMT-0.5 (name and verison passed to setup())
        self.build_dir =  os.path.join(self.dist_dir, self.dist_name+'-osx-build')



    def run(self):
        print("---------------------------------")
        print("Building PyMT Portable for OSX")
        print("---------------------------------")

        print("\nPreparing Build...")
        print("---------------------------------------")
        if os.path.exists(self.build_dir):
            print("*Cleaning old build dir")
            shutil.rmtree(self.build_dir, ignore_errors=True)
        print("*Creating build directory:")
        print(" "+self.build_dir)
        os.makedirs(self.build_dir)


        print("\nGetting binary dependencies...")
        print("---------------------------------------")
        print("*Downloading:", self.deps_url)
        #report_hook is called every time a piece of teh file is downloaded to print progress
        def report_hook(block_count, block_size, total_size):
            p = block_count*block_size*100.0/total_size
            print("\b\b\b\b\b\b\b\b\b", "%06.2f"%p +"%", end=' ')
        print(" Progress: 000.00%", end=' ')
        urlretrieve(self.deps_url, #location of binary dependencioes needed for portable pymt
                    os.path.join(self.build_dir,'deps.zip'), #tmp file to store teh archive
                    reporthook=report_hook)
        print(" [Done]")


        print("*Extracting binary dependencies...")
        #using osx sysetm command, becasue python zipfile cant handle the hidden files in teh archive
        Popen(['unzip', os.path.join(self.build_dir,'deps.zip')], cwd=self.build_dir, stdout=PIPE).communicate()

        print("\nPutting pymt into portable environment")
        print("---------------------------------------")
        print("*Building pymt source distribution")
        sdist_cmd = [sys.executable, #path to python.exe
                     os.path.join(self.src_dir,'setup.py'), #path to setup.py
                     'sdist', #make setup.py create a src distribution
                     '--dist-dir=%s'%self.build_dir] #put it into build folder
        Popen(sdist_cmd, stdout=PIPE).communicate()


        print("*Placing pymt source distribution in portable context")
        src_dist = os.path.join(self.build_dir,self.dist_name)
        #using osx sysetm command, becasue python zipfile cant handle the hidden files in teh archive
        Popen(['tar', 'xfv', src_dist+'.tar.gz'], cwd=self.build_dir, stdout=PIPE, stderr=PIPE).communicate()
        if self.no_cext:
            print("*Skipping C Extension build (either --no_cext or --no_mingw option set)")
        else:
            print("*Compiling C Extensions inplace for portable distribution")
            cext_cmd = [sys.executable, #path to python.exe
                        'setup.py',
                        'build_ext', #make setup.py create a src distribution
                        '--inplace'] #do it inplace
            #this time it runs teh setup.py inside the source distribution
            #thats has been generated inside the build dir (to generate ext
            #for teh target, instead of the source were building from)
            Popen(cext_cmd, cwd=src_dist, stdout=PIPE, stderr=PIPE).communicate()



        print("\nFinalizing Application Bundle")
        print("---------------------------------------")
        print("*Copying launcher script into the app bundle")
        script_target = os.path.join(self.build_dir, 'portable-deps-osx', 'PyMT.app', 'Contents', 'Resources', 'script')
        script = os.path.join(src_dist,'pymt','tools','packaging','osx', 'pymt.sh')
        shutil.copy(script, script_target)

        print("*Moving examples out of app bundle to be included in disk image")
        examples_target = os.path.join(self.build_dir, 'portable-deps-osx', 'examples')
        examples = os.path.join(src_dist,'examples')
        shutil.move(examples, examples_target)

        print("*Moving newly build pymt distribution into app bundle")
        pymt_target = os.path.join(self.build_dir, 'portable-deps-osx', 'PyMT.app', 'Contents', 'Resources', 'pymt')
        shutil.move(src_dist, pymt_target)

        print("*Removing intermediate file")
        os.remove(os.path.join(self.build_dir,'deps.zip'))
        os.remove(os.path.join(self.build_dir,src_dist+'.tar.gz'))
        shutil.rmtree(os.path.join(self.build_dir,'__MACOSX'), ignore_errors=True)


        #contents of portable-deps-osx, are now ready to go into teh disk image
        dmg_dir = os.path.join(self.build_dir, 'portable-deps-osx')
        vol_name = "PyMT"

        print("\nCreating disk image for distribution")
        print("---------------------------------------")
        print("\nCreating intermediate DMG disk image: temp.dmg")
        print("*checking how much space is needed for disk image...")
        du_cmd = 'du -sh %s'%dmg_dir
        du_out = Popen(shlex.split(du_cmd), stdout=PIPE).communicate()[0]
        size, unit = re.search('(\d+)(.*)\s+/.*', du_out).group(1,2)
        print("  build needs at least %s%s." % (size, unit))

        size = int(size)+10
        print("*allocating %d%s for temp.dmg (volume name:%s)" % (size, unit, vol_name))
        create_dmg_cmd = 'hdiutil create -srcfolder %s -volname %s -fs HFS+ \
                         -fsargs "-c c=64,a=16,e=16" -format UDRW -size %d%s temp.dmg' \
                         % (dmg_dir, vol_name, size+10, unit)
        Popen(shlex.split(create_dmg_cmd), cwd=self.build_dir).communicate()

        print("*mounting intermediate disk image:")
        mount_cmd = 'hdiutil attach -readwrite -noverify -noautoopen "temp.dmg"'
        Popen(shlex.split(mount_cmd), cwd=self.build_dir, stdout=PIPE).communicate()

        print("*running Apple Script to configure DMG layout properties:")
        dmg_config_script = """
           tell application "Finder"
             tell disk "%s"
                   open

                   set current view of container window to icon view
                   set toolbar visible of container window to false
                   set statusbar visible of container window to false
                   set the bounds of container window to {300,100,942,582}
                   set theViewOptions to the icon view options of container window
                   set arrangement of theViewOptions to not arranged
                   set icon size of theViewOptions to 72
                   set background picture of theViewOptions to file ".background:pymtdmg.png"
                   make new alias file at container window to POSIX file "/Applications" with properties {name:"Applications"}
                   set position of item "PyMT" of container window to {150, 130}
                   set position of item "Applications" of container window to {500, 130}
                   set position of item "examples" of container window to {575, 400}
                   set position of item "Readme.txt" of container window to {475, 400}
                   set position of item "make-symlinks" of container window to {375, 400}
                   close
                   open
                   update without registering applications
                   delay 2
                   eject
             end tell
           end tell
        """ % vol_name
        print(Popen(['osascript'], cwd=self.build_dir, stdin=PIPE, stdout=PIPE).communicate(dmg_config_script)[0])


        print("\nCreating final disk image")

        print("*unmounting intermediate disk image")
        umount_cmd = 'hdiutil detach /Volumes/%s' % vol_name
        Popen(shlex.split(umount_cmd), cwd=self.build_dir, stdout=PIPE).communicate()

        print("*compressing and finalizing disk image")
        convert_cmd = 'hdiutil convert "temp.dmg" -format UDZO -imagekey zlib-level=9 -o %s.dmg' % os.path.join(self.dist_dir,vol_name)
        Popen(shlex.split(convert_cmd), cwd=self.build_dir, stdout=PIPE).communicate()

        print("*Writing disk image, and cleaning build directory")
        shutil.rmtree(self.build_dir, ignore_errors=True)
