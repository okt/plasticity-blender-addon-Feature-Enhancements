import bpy
import math

from .__init__ import plasticity_client
from .__init__ import load_presets
from .client import FacetShapeType



class ConnectButton(bpy.types.Operator):
    bl_idname = "wm.connect_button"
    bl_label = "Connect"
    bl_description = "Connect to the Plasticity server"

    @classmethod
    def poll(cls, context):
        return not plasticity_client.connected

    def execute(self, context):
        server = context.scene.prop_plasticity_server
        plasticity_client.connect(server)
        
        # Load the refacet presets after connecting (not ideal, but works for now).
        load_presets(context.scene)
        
        return {'FINISHED'}


class DisconnectButton(bpy.types.Operator):
    bl_idname = "wm.disconnect_button"
    bl_label = "Disconnect"
    bl_description = "Disconnect from the Plasticity server"

    @classmethod
    def poll(cls, context):
        return plasticity_client.connected

    def execute(self, context):
        plasticity_client.disconnect()
        return {'FINISHED'}


class ListButton(bpy.types.Operator):
    bl_idname = "wm.list"
    bl_label = "Refresh"
    bl_description = "Refresh the list of available items"

    @classmethod
    def poll(cls, context):
        return plasticity_client.connected

    def execute(self, context):
        only_visible = context.scene.prop_plasticity_list_only_visible
        if only_visible:
            plasticity_client.list_visible()
        else:
            plasticity_client.list_all()
        return {'FINISHED'}


class SubscribeAllButton(bpy.types.Operator):
    bl_idname = "wm.subscribe_all"
    bl_label = "Subscribe All"
    bl_description = "Subscribe to all available meshes"

    @classmethod
    def poll(cls, context):
        return plasticity_client.connected and not plasticity_client.subscribed

    def execute(self, context):
        plasticity_client.subscribe_all()
        return {'FINISHED'}


class UnsubscribeAllButton(bpy.types.Operator):
    bl_idname = "wm.unsubscribe_all"
    bl_label = "Unsubscribe All"
    bl_description = "Unsubscribe to all available meshes"

    @classmethod
    def poll(cls, context):
        return plasticity_client.connected and plasticity_client.subscribed

    def execute(self, context):
        plasticity_client.unsubscribe_all()
        return {'FINISHED'}

class RefacetButton(bpy.types.Operator):
    bl_idname = "wm.refacet"
    bl_label = "Refacet"
    bl_description = "Refacet the mesh"

    @classmethod
    def poll(cls, context):
        if not plasticity_client.connected:
            return False
        return any("plasticity_id" in obj.keys() for obj in context.selected_objects)

    def execute(self, context):
        if len(context.scene.refacet_presets) > 0:       
            preset = context.scene.refacet_presets[context.scene.active_refacet_preset_index]
            
            curve_chord_tolerance = preset.tolerance
            surface_plane_tolerance = preset.tolerance
            curve_chord_angle = preset.angle
            surface_plane_angle = preset.angle                                    
        else:
            curve_chord_tolerance = context.scene.prop_plasticity_facet_tolerance
            surface_plane_tolerance = context.scene.prop_plasticity_facet_tolerance
            curve_chord_angle = context.scene.prop_plasticity_facet_angle
            surface_plane_angle = context.scene.prop_plasticity_facet_angle

        max_sides = 3 if context.scene.prop_plasticity_facet_tri_or_ngon == "TRI" else 128
        plane_angle = math.pi / 4.0 if (max_sides > 4) else 0

        min_width = 0
        max_width = 0
        curve_chord_max = 0

        if context.scene.prop_plasticity_ui_show_advanced_facet:            
            if len(context.scene.refacet_presets) > 0: 
                surface_plane_tolerance = preset.Face_plane_tolerance
                surface_plane_angle = preset.Face_Angle_tolerance
                curve_chord_tolerance = preset.Edge_chord_tolerance
                curve_chord_angle = preset.Edge_Angle_tolerance
                min_width = preset.min_width
                max_width = preset.max_width            
            else:
                surface_plane_tolerance = context.scene.prop_plasticity_surface_plane_tolerance
                surface_plane_angle = context.scene.prop_plasticity_surface_angle_tolerance
                curve_chord_tolerance = context.scene.prop_plasticity_curve_chord_tolerance            
                curve_chord_angle = context.scene.prop_plasticity_curve_angle_tolerance                
                min_width = context.scene.prop_plasticity_facet_min_width
                max_width = context.scene.prop_plasticity_facet_max_width
            if max_width > 0 and max_width < min_width:
                max_width = min_width
                
            curve_chord_max = max_width * math.sqrt(0.5)

        plasticity_ids_by_filename = {}
        
        for obj in context.selected_objects:
            if "plasticity_filename" in obj.keys():
                if obj["plasticity_filename"] not in plasticity_ids_by_filename.keys():
                    plasticity_ids_by_filename[obj["plasticity_filename"]] = []
                plasticity_ids_by_filename[obj["plasticity_filename"]].append(
                    obj["plasticity_id"])

        for filename, plasticity_ids in plasticity_ids_by_filename.items():
            plasticity_client.refacet_some(filename,
                                           plasticity_ids,
                                           relative_to_bbox=True,
                                           curve_chord_tolerance=curve_chord_tolerance,
                                           curve_chord_angle=curve_chord_angle,
                                           surface_plane_tolerance=surface_plane_tolerance,
                                           surface_plane_angle=surface_plane_angle,
                                           match_topology=True,
                                           max_sides=max_sides,
                                           plane_angle=plane_angle,
                                           min_width=min_width,
                                           max_width=max_width,
                                           curve_chord_max=curve_chord_max,
                                           shape=FacetShapeType.CUT)

        return {'FINISHED'}

class PlasticityPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_plasticity_panel"
    bl_label = "Plasticity"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Plasticity'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if plasticity_client.connected:
            disconnect_button = layout.operator(
                "wm.disconnect_button", text="Disconnect")
            layout.label(text="Connected to " + plasticity_client.server)
        else:
            box = layout.box()
            connect_button = box.operator(
                "wm.connect_button", text="Connect")
            box.prop(scene, "prop_plasticity_server", text="Server")

        if plasticity_client.connected:
            if plasticity_client.filename:
                layout.label(text="Filename: " + plasticity_client.filename)

            layout.separator()

            box = layout.box()
            box.prop(scene, "prop_plasticity_list_only_visible",
                     text="Only visible")
            box.operator("wm.list", text="Refresh")
            box.prop(scene, "prop_plasticity_unit_scale",
                     text="Scale", slider=True)

            layout.separator()
            
            if not plasticity_client.subscribed:
                layout.operator("wm.subscribe_all", text="Live link")
            else:
                layout.operator("wm.unsubscribe_all", text="Disable live link")
            layout.separator()

            box = layout.box()
            refacet_op = box.operator("wm.refacet", text="Refacet")                      
            box.label(text="Refacet Presets")
            
            row = box.row()
            row.template_list("OBJECT_UL_RefacetPresetsList", "refacet_presets", context.scene, "refacet_presets", context.scene, "active_refacet_preset_index")
            
            col = row.column(align=True)
            col.operator("refacet_preset.add", icon='ADD', text="")
            col.operator("refacet_preset.remove", icon='REMOVE', text="")
            
            box.prop(context.scene, "prop_plasticity_ui_show_advanced_facet", icon="TRIA_DOWN" if context.scene.prop_plasticity_ui_show_advanced_facet else "TRIA_RIGHT")
            box.prop(scene, "prop_plasticity_facet_tri_or_ngon", text="Tri or Ngon", expand=True)     
            
            if len(context.scene.refacet_presets) > 0:
                preset = context.scene.refacet_presets[context.scene.active_refacet_preset_index]                
            
            if context.scene.prop_plasticity_ui_show_advanced_facet:
                if len(scene.refacet_presets) > 0:
                    box.prop(preset, 'min_width')
                    box.prop(preset, 'max_width')
                    box.prop(preset, 'Edge_chord_tolerance')
                    box.prop(preset, 'Edge_Angle_tolerance')
                    box.prop(preset, 'Face_plane_tolerance')
                    box.prop(preset, 'Face_Angle_tolerance')
                    
                else:              
                    box.prop(scene, "prop_plasticity_facet_min_width", text="Min width")
                    box.prop(scene, "prop_plasticity_facet_max_width", text="Max width", slider=False)
                    box.prop(scene, "prop_plasticity_curve_chord_tolerance", text="Edge Chord Tolerance")
                    box.prop(scene, "prop_plasticity_curve_angle_tolerance", text="Edge Angle Tolerance")
                    box.prop(scene, "prop_plasticity_surface_plane_tolerance", text="Face Plane Tolerance")
                    box.prop(scene, "prop_plasticity_surface_angle_tolerance", text="Face Angle Tolerance")
            else:
                if len(scene.refacet_presets) > 0:
                    box.prop(preset, 'tolerance')
                    box.prop(preset, 'angle')
                else:
                    box.prop(scene, "prop_plasticity_facet_tolerance", text="Tolerance")
                    box.prop(scene, "prop_plasticity_facet_angle", text="Angle")
            
            layout.separator()
            box = layout.box()
            box.label(text="Utilities:")

            box.operator("mesh.auto_mark_edges", text="Auto Mark Edges")
            box.operator("mesh.merge_uv_seams", text="Merge UV Seams")

            box.operator("mesh.select_by_plasticity_face_id",
                         text="Select Plasticity Face(s)")
            box.operator("mesh.select_by_plasticity_face_id_edge",
                         text="Select Plasticity Edges")
            box.operator("mesh.paint_plasticity_faces",
                         text="Paint Plasticity Faces")
            box.operator("object.select_similar_geometry", text="Select Similar Geometry")
            box.operator("object.join_selected", text="Join Selected")
            box.operator("object.unjoin_selected", text="Unjoin Selected")
            box.operator("object.merge_nonoverlapping_meshes", text="Merge Non-overlapping Meshes")
            box.prop(scene, "overlap_threshold", text="Overlap Threshold") 
            box.operator("object.open_uv_editor", text="Open Selected Inside UV Editor")
