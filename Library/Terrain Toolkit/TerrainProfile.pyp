<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainProfile.py</Name>
    <Title>Terrain Profile &amp; Sections</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Profile</Text>
    <Parameters>
      <Parameter>
        <Name>SelectionExp</Name>
        <Text>1. Selection in the model</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>SelectRole</Name>
            <Text>Next selection is</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>SelectRole_0</Name>
                <Text>Terrain (ground)</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_1</Name>
                <Text>Second surface (optional)</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_2</Name>
                <Text>Alignment (polyline)</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>SelectionInfo</Name>
            <Text>Selected</Text>
            <Value>nothing yet</Value>
            <ValueType>Text</ValueType>
          </Parameter>
          <Parameter>
            <Name>ClearRow</Name>
            <Text>Selection</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>ClearButton</Name>
                <Text>Clear current</Text>
                <ValueType>Button</ValueType>
                <EventId>1002</EventId>
              </Parameter>
              <Parameter>
                <Name>ClearAllButton</Name>
                <Text>Clear all</Text>
                <ValueType>Button</ValueType>
                <EventId>1003</EventId>
              </Parameter>
            </Parameters>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>TerrainSourceExp</Name>
        <Text>2. Terrain source</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>TerrainSource</Name>
            <Text>Terrain from</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>TerrainSource_0</Name>
                <Text>Selection in model</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>TerrainSource_1</Name>
                <Text>File (LandXML, XYZ/CSV, ASC, OBJ)</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>TerrainFile</Name>
            <Text>Terrain file</Text>
            <Value></Value>
            <ValueType>String</ValueType>
            <ValueDialog>OpenFileDialog</ValueDialog>
            <FileFilter>Terrain files (*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts)|*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts|All files (*.*)|*.*|</FileFilter>
            <FileExtension>xml</FileExtension>
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>FileUnits</Name>
            <Text>File units</Text>
            <Value>m</Value>
            <ValueType>StringComboBox</ValueType>
            <ValueList>m|mm|cm|dm|km|ft|us-ft</ValueList>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>FileLayout</Name>
            <Text>Point file columns</Text>
            <Value>auto</Value>
            <ValueType>StringComboBox</ValueType>
            <ValueList>auto|XYZ|PXYZ|PXYZD|PYXZ|YXZ|PNEZ|PNEZD|PENZ|PENZD|NEZ|ENZ</ValueList>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>GridStep</Name>
            <Text>ASC grid: use every n-th cell</Text>
            <Value>1</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1</MinValue>
            <MaxValue>100</MaxValue>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ObjYUp</Name>
            <Text>OBJ file is Y-up</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ShiftInfo</Name>
            <Text>Coordinate shift = real-world coordinates of the Allplan origin (m)</Text>
            <Value></Value>
            <ValueType>Text</ValueType>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ShiftRow</Name>
            <Text>Shift X / Y (m)</Text>
            <ValueType>Row</ValueType>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
            <Parameters>
              <Parameter>
                <Name>ShiftX</Name>
                <Text>X</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
              <Parameter>
                <Name>ShiftY</Name>
                <Text>Y</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>ShiftZ</Name>
            <Text>Shift Z (m)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>TerrainSource == 1 or DesignSource == 1</Visible>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>DesignExp</Name>
        <Text>2b. Second surface from file (optional)</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>DesignSource</Name>
            <Text>Second surface from</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>DesignSource_0</Name>
                <Text>Selection in model</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>DesignSource_1</Name>
                <Text>File</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>DesignFile</Name>
            <Text>Second surface file</Text>
            <Value></Value>
            <ValueType>String</ValueType>
            <ValueDialog>OpenFileDialog</ValueDialog>
            <FileFilter>Terrain files (*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts)|*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts|All files (*.*)|*.*|</FileFilter>
            <FileExtension>xml</FileExtension>
            <Visible>DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>GroundName</Name>
            <Text>Name of ground line</Text>
            <Value>Ground</Value>
            <ValueType>String</ValueType>
          </Parameter>
          <Parameter>
            <Name>DesignName</Name>
            <Text>Name of second line</Text>
            <Value>Design</Value>
            <ValueType>String</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>ProfExp</Name>
        <Text>3. Drawing</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>ProfileMode</Name>
            <Text>Create</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>ProfileMode_0</Name>
                <Text>Long section</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>ProfileMode_1</Name>
                <Text>Cross sections</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>ProfileMode_2</Name>
                <Text>Both</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>Reverse</Name>
            <Text>Reverse alignment direction</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>StationInterval</Name>
            <Text>Station interval (m)</Text>
            <Value>20.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.1</MinValue>
          </Parameter>
          <Parameter>
            <Name>VExaggeration</Name>
            <Text>Vertical exaggeration</Text>
            <Value>10.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.1</MinValue>
          </Parameter>
          <Parameter>
            <Name>ZInterval</Name>
            <Text>Elevation grid interval (m)</Text>
            <Value>1.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.01</MinValue>
          </Parameter>
          <Parameter>
            <Name>Grid</Name>
            <Text>Grid</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>Table</Name>
            <Text>Station / elevation table</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>Title</Name>
            <Text>Title</Text>
            <Value>Long section</Value>
            <ValueType>String</ValueType>
          </Parameter>
          <Parameter>
            <Name>SectionInterval</Name>
            <Text>Cross section interval (m)</Text>
            <Value>20.0</Value>
            <ValueType>Double</ValueType>
            <Visible>ProfileMode != 0</Visible>
          </Parameter>
          <Parameter>
            <Name>WidthRow</Name>
            <Text>Width left / right (m)</Text>
            <ValueType>Row</ValueType>
            <Visible>ProfileMode != 0</Visible>
            <Parameters>
              <Parameter>
                <Name>LeftWidth</Name>
                <Text>L</Text>
                <Value>15.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
              <Parameter>
                <Name>RightWidth</Name>
                <Text>R</Text>
                <Value>15.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>SectionColumns</Name>
            <Text>Sections per row</Text>
            <Value>4</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1</MinValue>
            <Visible>ProfileMode != 0</Visible>
          </Parameter>
          <Parameter>
            <Name>SectionLinesInPlan</Name>
            <Text>Section lines in plan</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>ProfileMode != 0</Visible>
          </Parameter>
          <Parameter>
            <Name>SectionLineProp</Name>
            <Text>Section line format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>ProfileMode != 0</Visible>
          </Parameter>
          <Parameter>
            <Name>DrawingScale</Name>
            <Text>Drawing scale 1 :</Text>
            <Value>500.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>1</MinValue>
          </Parameter>
          <Parameter>
            <Name>TextHeight</Name>
            <Text>Text height (mm)</Text>
            <Value>2.5</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.1</MinValue>
          </Parameter>
          <Parameter>
            <Name>Decimals</Name>
            <Text>Decimals</Text>
            <Value>2</Value>
            <ValueType>Integer</ValueType>
            <MinValue>0</MinValue>
            <MaxValue>4</MaxValue>
          </Parameter>
          <Parameter>
            <Name>AutoPlace</Name>
            <Text>Place drawing right of the terrain</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>PlaceRow</Name>
            <Text>Drawing origin X / Y (m)</Text>
            <ValueType>Row</ValueType>
            <Visible>AutoPlace == False</Visible>
            <Parameters>
              <Parameter>
                <Name>PlaceX</Name>
                <Text>X</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
              <Parameter>
                <Name>PlaceY</Name>
                <Text>Y</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>GroundProp</Name>
            <Text>Ground line format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
          <Parameter>
            <Name>DesignProp</Name>
            <Text>Second line format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
          <Parameter>
            <Name>GridProp</Name>
            <Text>Grid format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
          <Parameter>
            <Name>FrameProp</Name>
            <Text>Frame format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
          <Parameter>
            <Name>TextProp</Name>
            <Text>Text format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>PlanExp</Name>
        <Text>4. In plan</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>Drape3D</Name>
            <Text>Alignment draped on terrain (3D)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DrapeProp</Name>
            <Text>Draped line format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>Drape3D == True</Visible>
          </Parameter>
          <Parameter>
            <Name>StationLabels</Name>
            <Text>Station labels along the alignment</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>ReportFile</Name>
            <Text>Profile points (CSV, optional)</Text>
            <Value></Value>
            <ValueType>String</ValueType>
            <ValueDialog>SaveFileDialog</ValueDialog>
            <FileFilter>CSV files (*.csv)|*.csv|All files (*.*)|*.*|</FileFilter>
            <FileExtension>csv</FileExtension>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>RunExp</Name>
        <Text>Create</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>RunButtonRow</Name>
            <Text>Run the tool</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>RunButton</Name>
                <Text>Create</Text>
                <ValueType>Button</ValueType>
                <EventId>1001</EventId>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>ResultInfo</Name>
            <Text>Last result</Text>
            <Value>-</Value>
            <ValueType>Text</ValueType>
          </Parameter>
          <Parameter>
            <Name>ShowResult</Name>
            <Text>Show result message</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>DiagExp</Name>
        <Text>Diagnostics</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>VerboseLog</Name>
            <Text>Verbose log (Trace window)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DiagRow</Name>
            <Text>Log</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>OpenLogButton</Name>
                <Text>Open log folder</Text>
                <ValueType>Button</ValueType>
                <EventId>1098</EventId>
              </Parameter>
              <Parameter>
                <Name>EnvButton</Name>
                <Text>Environment</Text>
                <ValueType>Button</ValueType>
                <EventId>1099</EventId>
              </Parameter>
            </Parameters>
          </Parameter>
        </Parameters>
      </Parameter>
    </Parameters>
  </Page>
</Element>
