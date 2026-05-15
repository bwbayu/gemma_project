"""Manim class/method introspection tools for the Coder agent.

Classes are eagerly walked at import time and cached in `MANIM_CLASSES` so
agent lookups stay O(1) — we pay the walk cost once instead of on every call.
"""

import pkgutil, importlib, inspect, sys

def _collect_manim_classes() -> dict[str, type]:
    """
    Walk the manim package and collect all public classes.

    Returns a flat dict: {"ClassName": <class object>, ...}
    """
    import manim

    classes: dict[str, type] = {}

    # enumerate every module in the manim package tree (e.g. manim.animation.creation)
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=manim.__path__,
        prefix="manim.",
        onerror=lambda _x: None,  # skip modules that can't be found
    ):
        try:
            # load the module
            module = importlib.import_module(modname)
        except Exception:
            # skip manim modules that need optional dependencies or raise any import error
            continue
        
        # inspect the module, take public classes, and store them in classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not name.startswith("_") and obj.__module__.startswith("manim"):
                classes[name] = obj

    return classes

"""
Load Manim Classes
"""
print("Manim Docs Tools: Loading ManimCE classes...", file=sys.stderr)
try:
    MANIM_CLASSES = _collect_manim_classes()
except ImportError as e:
    raise RuntimeError("ManimCE is not installed. Run: pip install manim") from e
print(f"Manim Docs Tools: Indexed {len(MANIM_CLASSES)} classes.", file=sys.stderr)

"""
Manim Function Tools
"""

def _ok(data: dict) -> dict:
    """Wrap data in a standard success response envelope."""
    return {"status": "success", "data": data, "error": None}


def _err(message: str, data: dict | None = None) -> dict:
    """Wrap a message in a standard error response envelope."""
    return {"status": "error", "data": data or {}, "error": message}


def get_class_info(class_name: str) -> dict:
    """
    Return constructor signature (constructor parameter), docstring, and inheritance for a class.
    """
    # get class
    cls = MANIM_CLASSES.get(class_name)

    # if not found, return feedback about related class
    if cls is None:
        # find suggested class based on substring match with class_name
        close = [k for k in MANIM_CLASSES if class_name.lower() in k.lower()][:5]
        return _err(
            f"Class '{class_name}' not found in ManimCE.",
            {"did_you_mean": close},
        )
    
    # get constructor parameter from class
    try:
        sig = str(inspect.signature(cls.__init__))
        # remove self parameter
        if sig.startswith("(self, "):
            sig = "(" + sig[7:]
        elif sig.startswith("(self)"):
            # if parameter only contain self
            sig = "()"
    except (ValueError, TypeError):
        sig = "(...)"

    # get docstring
    doc = inspect.getdoc(cls) or "No docstring available."

    # get parent class using MRO (Method Resolution Order) to get full inheritance chain
    parent = [b.__name__ for b in cls.__mro__[1:] if b.__name__ != "object"]

    return _ok({
        "class": class_name,
        "module": cls.__module__,
        "signature": f"{class_name}{sig}",
        "base_classes": parent[:5],
        "docstring": doc[:800],
        "note": "From the INSTALLED ManimCE package — guaranteed accurate.",
    })

def get_class_info_batch(class_names: list[str]) -> dict:
    """
    Get ManimCE class info for one or many classes in a single call.
    """
    results = {name: get_class_info(name) for name in dict.fromkeys(class_names)}
    
    return _ok({
        "results": results,
        "count": len(results),
    })


def search_manim_classes(query: str, limit: int = 10) -> dict:
    """
    Search classes by name and docstring keyword.

    Scoring algorithm:
    +100 = exact name match (case-insensitive) — highest priority
    +10 = query appears anywhere in name — partial match
    +5 = query appears in docstring — semantic match
    """
    query_lower = query.lower()
    results = []

    # iterate through all classes
    for name, cls in MANIM_CLASSES.items():
        score = 0
        if query_lower == name.lower():
            score += 100
        elif query_lower in name.lower():
            score += 10
        doc = inspect.getdoc(cls) or ""
        if query_lower in doc.lower():
            score += 5
        if score > 0:
            first_line = (doc.split("\n")[0])[:100] if doc else ""
            results.append((score, name, first_line))

    # sort based on score descending
    results.sort(key=lambda x: (-x[0], x[1]))
    return _ok({
        "query": query,
        "matches": [
            {"class": name, "description": desc}
            for _, name, desc in results[:limit]
        ],
        "total_found": len(results),
    })

def list_animation_classes() -> dict:
    """
    Return all classes that subclass manim.Animation.
    """
    from manim import Animation

    result = {}

    # iterate through all classes
    for name, cls in sorted(MANIM_CLASSES.items()):
        try:
            # filter for Animation module
            if issubclass(cls, Animation) and cls is not Animation:
                doc = inspect.getdoc(cls) or ""
                result[name] = doc.split("\n")[0][:100]
        except TypeError:
            # issubclass raises TypeError for non-class objects — skip
            continue
    return _ok({"animation_classes": result, "count": len(result)})

def list_mobject_classes() -> dict:
    """
    Return all classes that subclass manim.Mobject but NOT Animation.
    """
    from manim import Mobject, Animation

    result = {}

    # iterate through all classes
    for name, cls in sorted(MANIM_CLASSES.items()):
        try:
            # filter for Mobject module and not Animation object
            if (
                issubclass(cls, Mobject)
                and cls is not Mobject
                and not issubclass(cls, Animation)
            ):
                doc = inspect.getdoc(cls) or ""
                result[name] = doc.split("\n")[0][:100]
        except TypeError:
            continue
    return _ok({"mobject_classes": result, "count": len(result)})

def get_class_methods(class_name: str) -> dict:
    """
    Return all public methods of a class with their signatures.
    """
    # get classes
    cls = MANIM_CLASSES.get(class_name)
    if cls is None:
        return _err(f"Class '{class_name}' not found in ManimCE.")

    methods = {}

    # collect callable public methods from class
    for name, method in inspect.getmembers(cls):
        if name.startswith("_"):
            # skip private methods
            continue
        if inspect.isclass(method) or not callable(method):
            continue

        try:
            # get parameter method
            sig = str(inspect.signature(method))

            # get docstring method
            doc = (inspect.getdoc(method) or "").split("\n")[0][:100]

            methods[name] = {"signature": f"{name}{sig}", "description": doc}
        except (ValueError, TypeError):
            methods[name] = {"signature": f"{name}(...)", "description": ""}

    return _ok({"class": class_name, "methods": methods, "count": len(methods)})

def get_method_info(class_name: str, method_name: str) -> dict:
    """
    Return specific method of a class with their signatures.
    """
    # get classes
    cls = MANIM_CLASSES.get(class_name)
    if cls is None:
        return _err(f"Class '{class_name}' not found in ManimCE.")
    
    # reject private/internal methods
    if method_name.startswith("_"):
        return _err(f"Method '{method_name}' is private/internal and not exposed.")
    
    # get class attribute by name
    obj = getattr(cls, method_name, None)
    if obj is None:
        return _err(
            f"Method '{method_name}' from class '{class_name}' not found in ManimCE."
        )
    if not callable(obj):
        return _err(
            f"Attribute '{method_name}' on class '{class_name}' is not callable."
        )
    
    try:
        # get parameter method
        sig = str(inspect.signature(obj))

        # get docstring method
        doc = (inspect.getdoc(obj) or "").split("\n")[0][:100]
        return _ok({
            "class": class_name,
            "method": method_name,
            "signature": f"{method_name}{sig}",
            "description": doc,
        })
    except (ValueError, TypeError):
        return _ok({
            "class": class_name,
            "method": method_name,
            "signature": f"{method_name}(...)",
            "description": "",
        })

def get_direction_constants() -> dict:
    """
    Return the most commonly needed Manim constants.
    """
    import manim

    constants = {}
    for name in [
        "UP", "DOWN", "LEFT", "RIGHT", "ORIGIN",
        "UL", "UR", "DL", "DR",
        "OUT", "IN",
        "TAU", "PI", "DEGREES",
        "SMALL_BUFF", "MED_SMALL_BUFF", "MED_LARGE_BUFF", "LARGE_BUFF",
        "DEFAULT_FONT_SIZE",
    ]:
        val = getattr(manim, name, None)
        if val is not None:
            try:
                constants[name] = repr(val)
            except Exception:
                pass
    return _ok({"constants": constants})
