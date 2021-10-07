import bpy
import os
from bpy.props import StringProperty,PointerProperty,BoolProperty
from mathutils import Matrix,Vector
from math import degrees
import json
import subprocess

bl_info = {
    "name": "Generate character from attributes",
    "author": "Boulbayam",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "View3D",
    "description": "Generate character from attributes",
    "warning": "",
    "category": "GCFA",
}

def clean_name(name):
    # Retrieve the correct object name removing 001 of duplicates
    cleanName = name.split(".")
    if cleanName[-1].isnumeric():
        cleanName = cleanName[:-1]
    cleanName = ".".join(cleanName)
    
    return cleanName

class PropsSet(bpy.types.PropertyGroup):
    mainCharFile: StringProperty(subtype="FILE_PATH", name="Base character file")
    attribFolder: StringProperty(subtype="DIR_PATH", name="Attributes folder")
    jsonFile: StringProperty(subtype="FILE_PATH", name="Exported json file")
    fbxFile: StringProperty(subtype="FILE_PATH", name="Exported fbx file")
    ignoreNaming: BoolProperty(name="Ignore naming")
    fbxConverterExec: StringProperty(subtype="FILE_PATH", name="Fbx converter exec")
    fbxConvert: BoolProperty(name="Convert fbx")
    
    
class GCFA_OP_Generate(bpy.types.Operator):
    bl_idname = "gfca.generate"
    bl_label = "Generate"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        scn = context.scene
        gfca = scn.gfca

        # if true it will not transform the breasts
        ignoreBreast = True
        
        bpy.ops.object.select_all(action="DESELECT")
        
        if gfca.mainCharFile != "":
            # Import main fbx file
            mainCharFbx = bpy.path.abspath(gfca.mainCharFile)
            conv = 0
            # Execute the converter for main
            if gfca.fbxConvert and gfca.fbxConverterExec != "":
                fbxMainCharConverted = os.path.join(os.path.dirname(mainCharFbx),"converted_"+os.path.basename(mainCharFbx))
                subprocess.run([gfca.fbxConverterExec, mainCharFbx,fbxMainCharConverted])
                mainCharFbx = fbxMainCharConverted
                conv = 1
            
            bpy.ops.import_scene.fbx(filepath=mainCharFbx,use_anim=False)
            if conv == 1:
                os.remove(mainCharFbx)
        
            mainCharObjects = context.selected_objects
            mainCharArmature = None
            mainCharMesh = []
            
            # Split armature from meshes
            for ob in mainCharObjects:
                if ob.type == "ARMATURE":
                    mainCharArmature = ob
                elif ob.type == "MESH":
                    mainCharMesh.append(ob)
            
            attributesData = []
            attribObjects = []
            
            if mainCharArmature or len(mainCharMesh)>0:
                if gfca.attribFolder != "":
                    for fold in os.walk(bpy.path.abspath(gfca.attribFolder)):
                        for fileName in fold[2]:
                            if fileName.lower().endswith(".fbx"):
                                bpy.ops.object.select_all(action='DESELECT')

                                # Full attrib fbx path
                                fbxAttribPath = os.path.join(fold[0],fileName)
                                attributeName = os.path.splitext(fileName)[0]
                                
                                # Remove attrib objects if there is any
                                for attOb in attribObjects:
                                    bpy.data.objects.remove(attOb)
                                    
                                fbxAttPath = fbxAttribPath
                                conv = 0
                                # Execute the converter for the attributes
                                if gfca.fbxConvert and gfca.fbxConverterExec != "":
                                    fbxAttribConverted = os.path.join(fold[0],"converted_"+fileName)
                                    subprocess.run([gfca.fbxConverterExec, fbxAttPath,fbxAttribConverted])
                                    fbxAttPath = fbxAttribConverted
                                    conv = 1
                                # Import attrib fbx
                                bpy.ops.import_scene.fbx(filepath=fbxAttPath,use_anim=False)
                                if conv == 1:
                                    os.remove(fbxAttPath)
                                
                                attribObjects = context.selected_objects
                                
                                bpy.ops.object.select_all(action='DESELECT')
                                
                                attribArmature = None
                                attribMesh = []
                                
                                # split armature from meshes
                                for ob in attribObjects:
                                    if ob.type == "ARMATURE":
                                        attribArmature = ob
                                    elif ob.type == "MESH":
                                        attribMesh.append(ob)
                                
                                allBoneTransforms = []
                                if attribArmature and mainCharArmature:
                                    cleanNameAttrArm = clean_name(attribArmature.name)
                                    cleanNameCharArm = clean_name(mainCharArmature.name)
                                    
                                    if cleanNameCharArm == cleanNameAttrArm:
                                        for bone in mainCharArmature.data.bones:
                                            try:
                                                # attribute bone
                                                attrBone = attribArmature.data.bones[bone.name]
                                                
                                                # head and tail location for the main bone
                                                headBone = Vector((round(bone.head[0],2),round(bone.head[1],2),round(bone.head[2],2)))
                                                tailBone = Vector((round(bone.tail[0],2),round(bone.tail[1],2),round(bone.tail[2],2)))
                                                
                                                # head and tail location for the attribute bone
                                                headAttrBone = Vector((round(attrBone.head[0],2),round(attrBone.head[1],2),round(attrBone.head[2],2)))
                                                tailAttrBone = Vector((round(attrBone.tail[0],2),round(attrBone.tail[1],2),round(attrBone.tail[2],2)))
                                                
                                                # attribute bone transforms are different then the main bone
                                                if headBone != headAttrBone or tailBone != tailAttrBone:
                                                    length = 0
                                                    if attrBone.parent:
                                                        length = attrBone.parent.length
                                                    
                                                    # Attrib bone location for UE
                                                    bone_translation = Matrix.Translation(Vector((0, length, 0)) + attrBone.head).to_translation()
                                                    trans = [round(bone_translation[0],4),round(bone_translation[1]*-1,4),round(bone_translation[2],4)]
                                                    
                                                    # Attrib bone rotation for UE
                                                    eulerRot = attrBone.matrix.to_euler()
                                                    rotat = [round(degrees(eulerRot[0]),4),round(degrees(eulerRot[1]*-1),4),round(degrees(eulerRot[2]*-1),4)]
                                                    
                                                    scale = [1,1,1]
                                                    
                                                    boneTransform = {
                                                        "BoneName":attrBone.name,
                                                        "Location":trans,
                                                        "Rotation":rotat,
                                                        "Scale":scale
                                                    }
                                                    allBoneTransforms.append(boneTransform)
                                                    
                                            except Exception as E:
                                                print("Bone {} don't exist in attribute armature bones".format(bone.name))
                                                print(E)

                                        for pb in attribArmature.pose.bones:
                                            if ignoreBreast:
                                                if "Breast" not in pb.name and "RibsTwist" not in pb.name:
                                                    ct = pb.constraints.get(pb.name)
                                                    if ct is not None:
                                                        ct.influence = 1
                                                        continue
                                                    ct = pb.constraints.new('COPY_TRANSFORMS')
                                                    ct.name = pb.name
                                                    ct.target = mainCharArmature
                                                    ct.subtarget = pb.name
                                            else:
                                                ct = pb.constraints.get(pb.name)
                                                if ct is not None:
                                                    ct.influence = 1
                                                    continue
                                                ct = pb.constraints.new('COPY_TRANSFORMS')
                                                ct.name = pb.name
                                                ct.target = mainCharArmature
                                                ct.subtarget = pb.name
                                
                                for charMesh in mainCharMesh:
                                    for attMesh in attribMesh:
                                        cleanNameAttr = clean_name(attMesh.name)
                                        cleanNameChar = clean_name(charMesh.name)
                                        
                                        cleanNameCharP1 = cleanNameChar.split("_")[0]
                                        cleanNameCharP2 = cleanNameChar.split("_")[-1]
                                        cleanNameAttrP1 = cleanNameAttr.split("_")[0]
                                        cleanNameAttrP2 = cleanNameAttr.split("_")[-1]
                                        
                                        if cleanNameChar == cleanNameAttr or gfca.ignoreNaming or (cleanNameCharP1 == cleanNameAttrP1 and cleanNameCharP2 == cleanNameAttrP2):
                                                              
                                            try:
                                                t = 0
                                                for k in attMesh.data.shape_keys.key_blocks:
                                                    if t == 1:
                                                        attMesh.shape_key_remove(k)
                                                    t = 1
                                                attMesh.shape_key_remove(attMesh.data.shape_keys.key_blocks[0])
                                            except:
                                                pass
                                            
                                            bpy.ops.object.select_all(action='DESELECT')
                                            context.view_layer.objects.active = attMesh
                                            attMesh.select_set(True)
                                            for modifier in attMesh.modifiers:
                                                bpy.ops.object.modifier_apply(modifier=modifier.name)
                                            bpy.ops.object.select_all(action='DESELECT')

                                            changedVertices = 0
                                            
                                            attMeshVerts  = attMesh.data.vertices
                                            charMeshVerts = charMesh.data.vertices
                                            
                                            # all attribute mesh vertices coordinates
                                            attMeshCo = [v.co for v in attMeshVerts]
                                            
                                            # Check if vertex coordinates are different
                                            for ver in range(0,len(attMeshVerts)):
                                                if attMeshVerts[ver].co != charMeshVerts[ver].co:
                                                    changedVertices = 1
                                                    break
                                                
                                            if changedVertices == 1:
                                                try:
                                                    # Create basis shape key if none exists
                                                    if not charMesh.data.shape_keys:
                                                        sk_basis = charMesh.shape_key_add(name='Basis')
                                                        sk_basis.interpolation = 'KEY_LINEAR'
                                                        charMesh.data.shape_keys.use_relative = True
                                                        
                                                    # Create a shapekey with attrib name
                                                    shape_key = charMesh.shape_key_add(name=attributeName)
                                                    shape_key.interpolation = 'KEY_LINEAR'
                                                    
                                                    # Assign new coordinates to shape key
                                                    for i in range(len(charMeshVerts)):
                                                        shape_key.data[i].co = attMeshCo[i]
                                                        
                                                except Exception as E:
                                                    print("Issue with shapekey {} !".format(attributeName))
                                                    print(E)
                                            break
                                
                                
                                attributeData = {"attributeName":attributeName,"BlendShapeName":attributeName,"BoneTransforms":allBoneTransforms}
                                attributesData.append(attributeData)
            
            # Remove attributes objects
            for attOb in attribObjects:
                bpy.data.objects.remove(attOb)

            if gfca.jsonFile != "":
                # Write json file
                with open(bpy.path.abspath(gfca.jsonFile), 'w') as outfile:
                    json.dump(attributesData, outfile ,indent=4)
            
            if gfca.fbxFile != "":
                # Deselect all objects in scene
                bpy.ops.object.select_all(action='DESELECT')
                # Select main objects
                for ob in mainCharObjects:
                    context.view_layer.objects.active = ob
                    ob.select_set(True)
                # Export selected objects as fbx
                bpy.ops.export_scene.fbx(filepath=bpy.path.abspath(gfca.fbxFile),use_selection=True)
                bpy.ops.object.select_all(action='DESELECT')
                
                
        return {"FINISHED"}
 
class GCFA_PT_Panel(bpy.types.Panel):
    bl_label = "Generate character from attributes"
    bl_idname = "ADD_PT_GEN_ATTR"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GCFA"
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def draw(self, context):
        layout = self.layout

        scn = bpy.context.scene
        gfca = scn.gfca

        row = layout.row()
        row.prop(gfca, "mainCharFile")
        
        row = layout.row()
        row.prop(gfca, "attribFolder")
        
        row = layout.row()
        row.prop(gfca, "jsonFile")
        
        row = layout.row()
        row.prop(gfca, "fbxFile")
        
        row = layout.row()
        row.prop(gfca, "ignoreNaming")
        
        row = layout.row()
        row.prop(gfca, "fbxConvert")
        
        if gfca.fbxConvert:
            row = layout.row()
            row.prop(gfca, "fbxConverterExec")
        
        row = layout.row()
        row.operator("gfca.generate")


classes = (
    PropsSet,
    GCFA_OP_Generate,
    GCFA_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.gfca = PointerProperty(type=PropsSet)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.gfca


if __name__ == "__main__":
    register()