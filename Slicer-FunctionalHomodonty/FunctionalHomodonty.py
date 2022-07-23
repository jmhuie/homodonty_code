import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# FunctionalHomodonty
#

class FunctionalHomodonty(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Functional Homodonty"  
    self.parent.categories = ["Quantification"] 
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Jonathan M. Huie"]  
    self.parent.helpText = """This module calculates functional homodonty from segmented teeth and jaws, as described by Cohen et al. 2020.
    For more information please see the <a href="https://github.com/jmhuie/Slicer-SegmentGeometry">online documentation</a>."""
    self.parent.acknowledgementText = """This module was developed by Jonathan M. Huie and Karly E. Cohen. JMH was supported by an NSF Graduate Research Fellowship (DGE-1746914)."""


    # Additional initialization step after application startup is complete
    #slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#


#
# FunctionalHomodontyWidget
#

class FunctionalHomodontyWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/FunctionalHomodonty.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = FunctionalHomodontyLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.segmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.JawLengthPointSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.JawJointPointSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.InLeverPointSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.ForceInputSlider.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.tableSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.SpecieslineEdit.connect('stateChanged(int)', self.updateParameterNodeFromGUI)

    # Buttons
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.ResetpushButton.connect('clicked(bool)', self.onResetButton)
    self.ui.PoscheckBox.connect('stateChanged(int)', self.onFlipCheckBox)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    #if not self._parameterNode.GetNodeReference("InputVolume"):
    #  firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    #  if firstVolumeNode:
    #    self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.segmentationSelector.setCurrentNode(self._parameterNode.GetNodeReference("Segmentation"))
    self.ui.JawLengthPointSelector.setCurrentNode(self._parameterNode.GetNodeReference("JawLength"))
    self.ui.JawJointPointSelector.setCurrentNode(self._parameterNode.GetNodeReference("JawJoint"))
    self.ui.InLeverPointSelector.setCurrentNode(self._parameterNode.GetNodeReference("InLever"))
    
    wasBlocked = self.ui.tableSelector.blockSignals(True)
    self.ui.tableSelector.setCurrentNode(self._parameterNode.GetNodeReference("ResultsTable"))
    self.ui.tableSelector.blockSignals(wasBlocked)

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("Segmentation") and self._parameterNode.GetNodeReference("JawLength") and self._parameterNode.GetNodeReference("JawJoint") and self._parameterNode.GetNodeReference("InLever"):
      self.ui.applyButton.toolTip = "Compute functional homodonty"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output parameters"
      self.ui.applyButton.enabled = False
      
    if self._parameterNode.GetNodeReference("ResultsTable"):
      self.ui.tableSelector.toolTip = "Edit output table"
    else:
      self.ui.tableSelector.toolTip = "Select output table"
      
    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("Segmentation", self.ui.segmentationSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("JawLength", self.ui.JawLengthPointSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("JawJoint", self.ui.JawJointPointSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("InLever", self.ui.InLeverPointSelector.currentNodeID)
    self._parameterNode.SetParameter("Force", str(self.ui.ForceInputSlider.value))
    self._parameterNode.SetNodeReferenceID("ResultsTable", self.ui.tableSelector.currentNodeID)
    

    self._parameterNode.EndModify(wasModified)

  def onFlipCheckBox(self):
    """
    Run processing when user clicks "Reset" button.
    """
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    shFolderItemId = shNode.GetItemByName("Functional Homodonty Misc")
    childIds = vtk.vtkIdList()
    shNode.GetItemChildren(shFolderItemId, childIds)

    if childIds.GetNumberOfIds() > 0:
      for itemIdIndex in range(childIds.GetNumberOfIds()):
        shItemId = childIds.GetId(itemIdIndex)
        dataNode = shNode.GetItemDataNode(shItemId)
        slicer.mrmlScene.RemoveNode(dataNode)
    
  def onResetButton(self):
    """
    Run processing when user clicks "Reset" button.
    """
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    shFolderItemId = shNode.GetItemByName("Functional Homodonty Misc")
    childIds = vtk.vtkIdList()
    shNode.GetItemChildren(shFolderItemId, childIds)
    self.ui.UpperradioButton.autoExclusive = False
    self.ui.LowerradioButton.autoExclusive = False
    self.ui.LeftradioButton.autoExclusive = False
    self.ui.RightradioButton.autoExclusive = False
    self.ui.UpperradioButton.checked = False
    self.ui.LowerradioButton.checked = False
    self.ui.LeftradioButton.checked = False
    self.ui.RightradioButton.checked = False
    self.ui.UpperradioButton.autoExclusive = True
    self.ui.LowerradioButton.autoExclusive = True
    self.ui.LeftradioButton.autoExclusive = True
    self.ui.RightradioButton.autoExclusive = True
    self.ui.PoscheckBox.checked = False

    if childIds.GetNumberOfIds() > 0:
      for itemIdIndex in range(childIds.GetNumberOfIds()):
        shItemId = childIds.GetId(itemIdIndex)
        dataNode = shNode.GetItemDataNode(shItemId)
        slicer.mrmlScene.RemoveNode(dataNode)
    shNode.RemoveItem(shFolderItemId)
    slicer.mrmlScene.RemoveNode(self.ui.tableSelector.currentNode())
    
    
    #self.ui.ResetpushButton.enabled = False

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      # Create nodes for results      
      tableNode = self.ui.tableSelector.currentNode()
      expTable = "Functional Homodonty Table"
      if not tableNode:
        tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", expTable)
        self.ui.tableSelector.setCurrentNode(tableNode)
      if tableNode.GetName() != expTable and slicer.mrmlScene.GetFirstNodeByName(expTable) != None:
        tableNode = slicer.mrmlScene.GetFirstNodeByName(expTable)
        self.ui.tableSelector.setCurrentNode(tableNode)
      if tableNode.GetName() != expTable and slicer.mrmlScene.GetFirstNodeByName(expTable) == None:
        tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", expTable)
        self.ui.tableSelector.setCurrentNode(tableNode)

      # Compute output
      self.logic.run(self.ui.segmentationSelector.currentNode(), self.ui.JawLengthPointSelector.currentNode(), self.ui.JawJointPointSelector.currentNode(), 
      self.ui.InLeverPointSelector.currentNode(), self.ui.ForceInputSlider.value, tableNode, self.ui.SpecieslineEdit.text, self.ui.LowerradioButton.checked, self.ui.UpperradioButton.checked,
      self.ui.LeftradioButton.checked, self.ui.RightradioButton.checked, self.ui.PoscheckBox.checked)
      
      self.ui.ResetpushButton.enabled = True  
 
    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()
#
# FunctionalHomodontyLogic
#

class FunctionalHomodontyLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Force"):
     parameterNode.SetParameter("Force", "1.0")


  def run(self, segmentationNode, lengthNode, jointNode, inleverNode, force, tableNode, species, LowerradioButton, UpperradioButton, LeftradioButton, RightradioButton, PoscheckBox):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param segmentation: segmentation file with all of the segmented teeth
    :param jawlength: markups line node measuring jaw length
    :param jawjoint: markups fiducial placed where the jaw joint is
    :param inlever: markups fiducial placed where the muscle insertion is on the jaw
    :param force: amount of force exerted by the muscles acting on the jaw
    :param tableNode: table to show results
    """

    import numpy as np

    logging.info('Processing started')

    if not segmentationNode:
      raise ValueError("Segmentation node is invalid")
    
    # Get visible segment ID list.
    # Get segment ID list
    visibleSegmentIds = vtk.vtkStringArray()
    segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    if visibleSegmentIds.GetNumberOfValues() == 0:
      raise ValueError("SliceAreaPlot will not return any results: there are no visible segments")
    
              
    # Make a table and set the first column as the slice number. 
    tableNode.RemoveAllColumns()
    table = tableNode.GetTable()
    
    SpeciesArray = vtk.vtkStringArray()
    SpeciesArray.SetName("Species")
    
    JawIDArray = vtk.vtkStringArray()
    JawIDArray.SetName("Jaw ID")
    
    SideArray = vtk.vtkStringArray()
    SideArray.SetName("Side of Face")
    
    SegmentNameArray = vtk.vtkStringArray()
    SegmentNameArray.SetName("Tooth ID")
    
    JawLengthArray = vtk.vtkFloatArray()
    JawLengthArray.SetName("Jaw Length")  
   
    RelPosArray = vtk.vtkFloatArray()
    RelPosArray.SetName("Rel Position")   
   
    PositionArray = vtk.vtkFloatArray()
    PositionArray.SetName("Position")
   
    SurfaceAreaArray = vtk.vtkFloatArray()
    SurfaceAreaArray.SetName("Surface Area (mm^2)")
    
    MechAdvArray = vtk.vtkFloatArray()
    MechAdvArray.SetName("Mechanical Advantage")  
    
    FToothArray = vtk.vtkFloatArray()
    FToothArray.SetName("F-Tooth (N)")    

    StressArray = vtk.vtkFloatArray()
    StressArray.SetName("Stress (N/m^2)")
    
    # create misc folder
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    newFolder = shNode.GetItemByName("Functional Homodonty Misc")
    if newFolder == 0:
      newFolder = shNode.CreateFolderItem(shNode.GetSceneItemID(), "Functional Homodonty Misc")      
    shNode.SetItemExpanded(newFolder,0)   
    # create models of the teeth
    slicer.modules.segmentations.logic().ExportAllSegmentsToModels(segmentationNode, newFolder) 

    # calculate the centroid and surface area of each segment
    import SegmentStatistics
    segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.enabled", str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.surface_area_mm2.enabled", str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.centroid_ras.enabled", str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_origin_ras.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_diameter_mm.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_x.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_y.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_z.enabled",str(True))
    segStatLogic.computeStatistics()
    stats = segStatLogic.getStatistics()

    jointRAS = [0,]*3
    jointNode.GetNthFiducialPosition(0,jointRAS)
	# draw line representing jaw length
    jawtipRAS = [0,]*3
    lengthNode.GetNthFiducialPosition(0,jawtipRAS)
    lengthLine = slicer.util.getFirstNodeByClassByName("vtkMRMLMarkupsLineNode", "JawLength")
    if lengthLine == None:
      lengthLine = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", "JawLength")
      lengthLine.GetDisplayNode().SetPropertiesLabelVisibility(False)
      lengthLine.AddControlPoint(jointRAS)
      lengthLine.AddControlPoint(jawtipRAS)
      shNode.SetItemParent(shNode.GetItemByDataNode(lengthLine), newFolder)
    else: 
      lengthLine.SetNthControlPointPosition(0,jointRAS) 
      lengthLine.SetNthControlPointPosition(1,jawtipRAS) 
    lengthLine.SetDisplayVisibility(0)

	
	# draw line representing in-lever
    inleverRAS = [0,]*3
    inleverNode.GetNthFiducialPosition(0,inleverRAS)
    leverLine = slicer.util.getFirstNodeByClassByName("vtkMRMLMarkupsLineNode", "InLever")
    if leverLine == None:
      leverLine = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", "InLever")
      leverLine.GetDisplayNode().SetPropertiesLabelVisibility(False)
      leverLine.AddControlPoint(jointRAS)
      leverLine.AddControlPoint(inleverRAS)
      shNode.SetItemParent(shNode.GetItemByDataNode(leverLine), newFolder)
    else: 
      leverLine.SetNthControlPointPosition(0,jointRAS)
      leverLine.SetNthControlPointPosition(1,inleverRAS) 
    leverLine.SetDisplayVisibility(0)
    
    # perform computations for each tooth 
    for segmentId in stats["SegmentIDs"]:
     
     if species != "Enter species name" and species != "":
       SpeciesArray.InsertNextValue(species)  
     if species == "Enter species name" or species == "": 
       species = "NA" 
       SpeciesArray.InsertNextValue(species)  
     jawID = "NA"
     if LowerradioButton == True:
       jawID = "Lower Jaw"
     if UpperradioButton == True:
       jawID = "Upper Jaw"
     if jawID != "":
       JawIDArray.InsertNextValue(jawID)
     side = "NA"
     if LeftradioButton == True:
       side = "Left"
     if RightradioButton == True:
       side = "Right"
     if side != "":
       SideArray.InsertNextValue(side)
        
     segment = segmentationNode.GetSegmentation().GetSegment(segmentId)
     SegmentNameArray.InsertNextValue(segment.GetName())
     
     
     JawLength = lengthLine.GetMeasurement('length').GetValue()
     JawLengthArray.InsertNextValue(JawLength)
     
     # measure surface area
     Area = stats[segmentId,"LabelmapSegmentStatisticsPlugin.surface_area_mm2"]/2
     SurfaceAreaArray.InsertNextValue(Area)
     
     # get tooth position at the base of the tooth
     obb_origin_ras = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_origin_ras"])
     obb_diameter_mm = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_diameter_mm"])
     obb_direction_ras_x = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_x"])
     obb_direction_ras_y = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_y"])
     obb_direction_ras_z = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_z"])
     if PoscheckBox == True:
       obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if (obb_direction_ras_z[2] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if (obb_direction_ras_z[1] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-5 * obb_direction_ras_z)
     else:
       obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if (obb_direction_ras_z[2] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if (obb_direction_ras_z[1] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
     modelNode = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", segment.GetName())

     if modelNode.GetParentTransformNode():
       transformModelToWorld = vtk.vtkGeneralTransform()
       slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(modelNode.GetParentTransformNode(), None, transformModelToWorld)
       polyTransformToWorld = vtk.vtkTransformPolyDataFilter()
       polyTransformToWorld.SetTransform(transformModelToWorld)
       polyTransformToWorld.SetInputData(modelNode.GetPolyData())
       polyTransformToWorld.Update()
       surface_World = polyTransformToWorld.GetOutput()
     else:
       surface_World = modelNode.GetPolyData()
     distanceFilter = vtk.vtkImplicitPolyDataDistance()
     distanceFilter.SetInput(surface_World)
     closestPointOnSurface_World = [0,0,0]
     distanceFilter.EvaluateFunctionAndGetClosestPoint(obb_center_ras, closestPointOnSurface_World)
     #slicer.mrmlScene.RemoveNode(modelNode)
     
     # draw line between jaw joint and tooth
     toothRAS = stats[segmentId,"LabelmapSegmentStatisticsPlugin.centroid_ras"] # draw to the center of tooth
     toothRAS = closestPointOnSurface_World # draw to the tip of the tooth
     ToothlineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", "temp_ToothPosLine")
     ToothlineNode.GetDisplayNode().SetPropertiesLabelVisibility(False)
     ToothlineNode.AddControlPoint(jointRAS)
     ToothlineNode.AddControlPoint(toothRAS)
     shNode.SetItemParent(shNode.GetItemByDataNode(ToothlineNode), newFolder)
     ToothPos = ToothlineNode.GetMeasurement('length').GetValue()
     PositionArray.InsertNextValue(ToothPos)
     slicer.mrmlScene.RemoveNode(ToothlineNode)

     
     # try to find the tip of the tooth
     obb_origin_ras = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_origin_ras"])
     obb_diameter_mm = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_diameter_mm"])
     obb_direction_ras_x = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_x"])
     obb_direction_ras_y = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_y"])
     obb_direction_ras_z = np.array(stats[segmentId,"LabelmapSegmentStatisticsPlugin.obb_direction_ras_z"])
     if PoscheckBox == True:
       obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if (obb_direction_ras_z[2] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if (obb_direction_ras_z[1] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
     else:
       obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if (obb_direction_ras_z[2] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
       if (obb_direction_ras_z[1] < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*-2 * obb_direction_ras_z)
       if all(obb_direction_ras_z < 0):
         obb_center_ras = obb_origin_ras+0.5*(obb_diameter_mm[0] * obb_direction_ras_x + obb_diameter_mm[1] * obb_direction_ras_y + obb_diameter_mm[2]*5 * obb_direction_ras_z)
     modelNode = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", segment.GetName())

     if modelNode.GetParentTransformNode():
       transformModelToWorld = vtk.vtkGeneralTransform()
       slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(modelNode.GetParentTransformNode(), None, transformModelToWorld)
       polyTransformToWorld = vtk.vtkTransformPolyDataFilter()
       polyTransformToWorld.SetTransform(transformModelToWorld)
       polyTransformToWorld.SetInputData(modelNode.GetPolyData())
       polyTransformToWorld.Update()
       surface_World = polyTransformToWorld.GetOutput()
     else:
       surface_World = modelNode.GetPolyData()
     distanceFilter = vtk.vtkImplicitPolyDataDistance()
     distanceFilter.SetInput(surface_World)
     closestPointOnSurface_World = [0,0,0]
     distanceFilter.EvaluateFunctionAndGetClosestPoint(obb_center_ras, closestPointOnSurface_World)
     slicer.mrmlScene.RemoveNode(modelNode)
     
     # draw line between jaw joint and tooth
     toothRAS = stats[segmentId,"LabelmapSegmentStatisticsPlugin.centroid_ras"] # draw to the center of tooth
     toothRAS = closestPointOnSurface_World # draw to the tip of the tooth
     lineNode = slicer.util.getFirstNodeByClassByName("vtkMRMLMarkupsLineNode",segment.GetName())
     if lineNode == None:
       lineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", segment.GetName())
       lineNode.GetDisplayNode().SetPropertiesLabelVisibility(False)
       lineNode.AddControlPoint(jointRAS)
       lineNode.AddControlPoint(toothRAS)
       shNode.SetItemParent(shNode.GetItemByDataNode(lineNode), newFolder)
     else: 
       lineNode.SetNthControlPointPosition(0,jointRAS)     
     OutLever = lineNode.GetMeasurement('length').GetValue()

     
     RelPosArray.InsertNextValue(ToothPos/JawLength)
     
     # calculate mechanical advantage and F-Tooth
     InLever = leverLine.GetMeasurement('length').GetValue()
     MA = InLever/OutLever
     MechAdvArray.InsertNextValue(MA)
     FToothArray.InsertNextValue(force * MA)
     
     # calculate tooth stress
     StressArray.InsertNextValue((force * MA)/ (Area * 1e-6))
    
    if species != "Enter species name" and species != "":
      tableNode.AddColumn(SpeciesArray)
      tableNode.SetColumnDescription(SpeciesArray.GetName(), "Species")

    if jawID != "":
      tableNode.AddColumn(JawIDArray)
      tableNode.SetColumnDescription(JawIDArray.GetName(), "If upper or lower jaw")
   
    if side != "":    
      tableNode.AddColumn(SideArray)
      tableNode.SetColumnDescription(SideArray.GetName(), "Side of face that the jaw is on")  
        
    tableNode.AddColumn(JawLengthArray)
    tableNode.SetColumnDescription(JawLengthArray.GetName(), "Jaw Length")
    tableNode.SetColumnUnitLabel(JawLengthArray.GetName(), "mm")  # TODO: use length unit
    
    tableNode.AddColumn(SegmentNameArray)
    tableNode.SetColumnDescription(SegmentNameArray.GetName(), "Tooth segment name")
    
    tableNode.AddColumn(PositionArray)
    tableNode.SetColumnDescription(PositionArray.GetName(), "Distance between the based of the tooth and the jaw joint")
    tableNode.SetColumnUnitLabel(PositionArray.GetName(), "mm")  # TODO: use length unit
    
    #tableNode.AddColumn(RelPosArray)
    #tableNode.SetColumnDescription(RelPosArray.GetName(), "Relative position of the tooth")
    #tableNode.SetColumnUnitLabel(RelPosArray.GetName(), "%")  # TODO: use length unit

    tableNode.AddColumn(SurfaceAreaArray)
    tableNode.SetColumnDescription(SurfaceAreaArray.GetName(), "Tooth surface area")
    tableNode.SetColumnUnitLabel(SurfaceAreaArray.GetName(), "mm^2")  # TODO: use length unit
    
    tableNode.AddColumn(MechAdvArray)
    tableNode.SetColumnDescription(MechAdvArray.GetName(), "Tooth mechanical advantage")

    tableNode.AddColumn(FToothArray)
    tableNode.SetColumnDescription(FToothArray.GetName(), "The force acting on a tooth (muscle force * mechanical advantage)")
    tableNode.SetColumnUnitLabel(FToothArray.GetName(), "N")  # TODO: use length unit

    tableNode.AddColumn(StressArray)
    tableNode.SetColumnDescription(StressArray.GetName(), "Tooth stress (tooth force / surface area)")


    customLayout = """
      <layout type=\"vertical\" split=\"true\" >
       <item splitSize=\"600\">
        <view class=\"vtkMRMLViewNode\" singletontag=\"1\">
         <property name=\"viewlabel\" action=\"default\">1</property>
        </view>
       </item>
       <item splitSize=\"400\">
        <view class=\"vtkMRMLTableViewNode\" singletontag=\"TableView1\">
         <property name=\"viewlabel\" action=\"default\">T</property>
        </view>
       </item>
      </layout>
      """
    customLayoutId=999

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)
    tableWidget = layoutManager.tableWidget(0)
    tableWidget.tableView().setMRMLTableNode(tableNode)    

    # Change layout to include plot and table      
#    slicer.app.layoutManager().setLayout(customLayoutId)
#    slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(tableNode.GetID())
#    slicer.app.applicationLogic().PropagateTableSelection()

    logging.info('Processing completed')
    

 

#
# FunctionalHomodontyTest
#

class FunctionalHomodontyTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_FunctionalHomodonty1()

  def test_FunctionalHomodonty1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    #inputVolume = SampleData.downloadSample('FunctionalHomodonty1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = FunctionalHomodontyLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
