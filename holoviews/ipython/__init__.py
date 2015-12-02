import os
import base64
from unittest import SkipTest

import param
import jinja2
from IPython.display import display, HTML

import holoviews
from ..element.comparison import ComparisonTestCase
from ..interface.collector import Collector
from ..plotting.renderer import Renderer
from ..plotting.widgets import NdWidget
from .archive import notebook_archive
from .magics import load_magics
from .display_hooks import display      # pyflakes:ignore (API import)
from .display_hooks import set_display_hooks, OutputMagic
from .parser import Parser
from .widgets import RunProgress

from param import ipython as param_ext

Collector.interval_hook = RunProgress
holoviews.archive = notebook_archive


class IPTestCase(ComparisonTestCase):
    """
    This class extends ComparisonTestCase to handle IPython specific
    objects and support the execution of cells and magic.
    """

    def setUp(self):
        super(IPTestCase, self).setUp()
        try:
            import IPython
            from IPython.display import HTML, SVG
            self.ip = IPython.InteractiveShell()
            if self.ip is None:
                raise TypeError()
        except Exception:
                raise SkipTest("IPython could not be started")

        self.addTypeEqualityFunc(HTML, self.skip_comparison)
        self.addTypeEqualityFunc(SVG,  self.skip_comparison)

    def skip_comparison(self, obj1, obj2, msg): pass

    def get_object(self, name):
        obj = self.ip._object_find(name).obj
        if obj is None:
            raise self.failureException("Could not find object %s" % name)
        return obj


    def cell(self, line):
        "Run an IPython cell"
        self.ip.run_cell(line, silent=True)

    def cell_magic(self, *args, **kwargs):
        "Run an IPython cell magic"
        self.ip.run_cell_magic(*args, **kwargs)


    def line_magic(self, *args, **kwargs):
        "Run an IPython line magic"
        self.ip.run_line_magic(*args, **kwargs)


def load_hvjs(logo=False):
    """
    Displays javascript and CSS to initialize HoloViews widgets.
    """
    # Evaluate load_notebook.html template with widgetjs code
    widgetjs, widgetcss = Renderer.embed_assets()
    templateLoader = jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__)))
    jinjaEnv = jinja2.Environment(loader=templateLoader)
    template = jinjaEnv.get_template('load_notebook.html')
    display(HTML(template.render({'widgetjs': widgetjs,
                                  'widgetcss': widgetcss,
                                  'logo': logo})))


# Populating the namespace for keyword evaluation
from ..core.options import Cycle, Palette, Store # pyflakes:ignore (namespace import)
import numpy as np                               # pyflakes:ignore (namespace import)

Parser.namespace = {'np':np, 'Cycle':Cycle, 'Palette': Palette}

class load_notebook_fn(param.ParameterizedFunction):
    """
    Parameterized function to initialize notebook resources
    and register magics.
    """

    bokeh = param.Boolean(default=False, doc="""Toggle inclusion of BokehJS,
        required to render plots using the Bokeh backend.""")

    css = param.String(default='', doc="Optional CSS rule set to apply to the notebook.")

    logo = param.Boolean(default=True, doc="Toggles display of HoloViews logo")

    width = param.Number(default=None, bounds=(0, 100), doc="""
        Width of the notebook as a percentage of the browser screen window width.""")

    _loaded = False

    def __call__(self, **params):
        p = param.ParamOverrides(self, params)

        if load_notebook_fn._loaded == False:
            ip = get_ipython()
            param_ext.load_ipython_extension(ip, verbose=False)
            load_magics(ip)
            OutputMagic.initialize()
            set_display_hooks(ip)
            load_notebook_fn._loaded = True

        css = ''
        if p.width is not None:
            css += '<style>div.container { width: %s%% }</style>' % p.width
        if p.css:
            css += '<style>%s</style>' % p.css
        if css:
            display(HTML(css))

        load_hvjs(logo=p.logo)
        if p.bokeh:
            import bokeh.io
            bokeh.io.load_notebook()
        

load_notebook = load_notebook_fn.instance()

def load_ipython_extension(ip):
    load_notebook()
    
def unload_ipython_extension(ip):
    load_notebook_fn._loaded = False
