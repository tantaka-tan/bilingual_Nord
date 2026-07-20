import bpy


class NodeRegistry:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.registered = set()

    def rebuild(self):
        self.registered = {
            name for name in dir(bpy.types)
            if name.startswith(("GeometryNode", "ShaderNode", "FunctionNode", "NodeGroup"))
            and isinstance(getattr(bpy.types, name, None), type)
        }
        return self.registered

    def exists(self, bl_idname):
        return bl_idname in self.registered or hasattr(bpy.types, bl_idname)
