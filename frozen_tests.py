# FreeCAD's Part, PartDesign and ShapeStorage tests with shape values frozen
# (Part's ImmutableShapeValues on), in one FreeCADCmd process. From this
# directory, or with FORK_TESTS=<this directory>:
#
#     FreeCADCmd -c "exec(open('frozen_tests.py').read())"
#
# under a pty (`script -qc "<cmd>" /dev/null` on Linux, `script -q /dev/null
# <cmd>` on macOS), as FreeCADCmd -t needs. freeze.py sets the preference for
# the run and puts the user's own value back before FreeCAD saves user.cfg; a
# crash leaves the run's value set, so check it afterwards. FROZEN_TESTS picks
# the modules (default the three). The plain run is FreeCADCmd -t <module>.
import os
import sys
import unittest

sys.path.insert(0, os.environ.get("FORK_TESTS", os.getcwd()))
from freeze import set_for_run  # noqa: E402

set_for_run(True)
import FreeCAD as App  # noqa: E402

print("ImmutableShapeValues",
      App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").GetBool("ImmutableShapeValues"))
for name in os.environ.get("FROZEN_TESTS", "TestPartApp TestPartDesignApp ShapeStorage").split():
    print("==", name, "frozen")
    suite = unittest.defaultTestLoader.loadTestsFromName(name)
    unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    sys.stdout.flush()
