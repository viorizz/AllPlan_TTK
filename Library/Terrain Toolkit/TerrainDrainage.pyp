<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainDrainage.py</Name>
    <Title>Terrain Drainage (water flow)</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Drainage</Text>
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
                <Text>Terrain mesh / points</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_1</Name>
                <Text>Flow start points / lines (optional)</Text>
                <Value>1</Value>
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
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>FileLayout</Name>
            <Text>Point file columns</Text>
            <Value>auto</Value>
            <ValueType>StringComboBox</ValueType>
            <ValueList>auto|XYZ|PXYZ|PXYZD|PYXZ|YXZ|PNEZ|PNEZD|PENZ|PENZD|NEZ|ENZ</ValueList>
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>GridStep</Name>
            <Text>ASC grid: use every n-th cell</Text>
            <Value>1</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1</MinValue>
            <MaxValue>100</MaxValue>
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ObjYUp</Name>
            <Text>OBJ file is Y-up</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ShiftInfo</Name>
            <Text>Coordinate shift = real-world coordinates of the Allplan origin (m)</Text>
            <Value></Value>
            <ValueType>Text</ValueType>
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>ShiftRow</Name>
            <Text>Shift X / Y (m)</Text>
            <ValueType>Row</ValueType>
            <Visible>TerrainSource == 1</Visible>
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
            <Visible>TerrainSource == 1</Visible>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>ArrowExp</Name>
        <Text>3. Flow direction</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>Arrows</Name>
            <Text>Flow arrows</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>ArrowSpacing</Name>
            <Text>Arrow grid spacing (m, 0 = per triangle)</Text>
            <Value>5.0</Value>
            <ValueType>Double</ValueType>
            <Visible>Arrows == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ArrowLength</Name>
            <Text>Arrow length (m, 0 = auto)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>Arrows == True</Visible>
          </Parameter>
          <Parameter>
            <Name>MinSlope</Name>
            <Text>Ignore slopes below (%)</Text>
            <Value>0.5</Value>
            <ValueType>Double</ValueType>
            <Visible>Arrows == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ScaleArrows</Name>
            <Text>Scale arrows by slope</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>Arrows == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ArrowProp</Name>
            <Text>Arrow format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>Arrows == True</Visible>
          </Parameter>
          <Parameter>
            <Name>FlowPaths</Name>
            <Text>Flow paths (steepest descent)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>SeedSpacing</Name>
            <Text>Start grid spacing if no start points (m, 0 = auto)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>FlowPaths == True</Visible>
          </Parameter>
          <Parameter>
            <Name>MinPathLength</Name>
            <Text>Drop paths shorter than (m)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>FlowPaths == True</Visible>
          </Parameter>
          <Parameter>
            <Name>FlowPathProp</Name>
            <Text>Flow path format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>FlowPaths == True</Visible>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>PondExp</Name>
        <Text>4. Low points &amp; ponding</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>Sinks</Name>
            <Text>Mark local low points</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>SinkLabels</Name>
            <Text>Label low point elevations</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>Sinks == True</Visible>
          </Parameter>
          <Parameter>
            <Name>SinkSize</Name>
            <Text>Marker size (m, 0 = auto)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>Sinks == True</Visible>
          </Parameter>
          <Parameter>
            <Name>SinkProp</Name>
            <Text>Low point format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>Sinks == True</Visible>
          </Parameter>
          <Parameter>
            <Name>Ponding</Name>
            <Text>Ponding depth map (depressions)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>MinDepth</Name>
            <Text>Minimum ponding depth (m)</Text>
            <Value>0.02</Value>
            <ValueType>Double</ValueType>
            <Visible>Ponding == True</Visible>
          </Parameter>
          <Parameter>
            <Name>PondingBreaks</Name>
            <Text>Depth class limits (m)</Text>
            <Value>0.02;0.1;0.25;0.5;1</Value>
            <ValueType>String</ValueType>
            <Visible>Ponding == True</Visible>
          </Parameter>
          <Parameter>
            <Name>OutputMode</Name>
            <Text>Output</Text>
            <Value>2</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>OutputMode_0</Name>
                <Text>3D coloured mesh</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>OutputMode_1</Name>
                <Text>2D colour fillings</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>OutputMode_2</Name>
                <Text>Both</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>LiftMesh</Name>
            <Text>Lift 3D map above terrain (m)</Text>
            <Value>0.02</Value>
            <ValueType>Double</ValueType>
            <Visible>OutputMode != 1</Visible>
          </Parameter>
          <Parameter>
            <Name>Legend</Name>
            <Text>Legend</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
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
            <Name>MaxFaces</Name>
            <Text>Max. faces per mesh element</Text>
            <Value>30000</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1000</MinValue>
          </Parameter>
          <Parameter>
            <Name>BaseProp</Name>
            <Text>Format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
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
