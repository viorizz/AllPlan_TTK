<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainPlatform.py</Name>
    <Title>Terrain Platform (pad grading)</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Platform</Text>
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
                <Text>Existing terrain</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_1</Name>
                <Text>Platform outline (closed)</Text>
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
        <Name>PadExp</Name>
        <Text>3. Platform</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>ElevationMode</Name>
            <Text>Pad elevation</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>ElevationMode_0</Name>
                <Text>Fixed elevation</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>ElevationMode_1</Name>
                <Text>Balance cut = fill</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>ElevationMode_2</Name>
                <Text>From 3D outline (best-fit plane)</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>Elevation</Name>
            <Text>Elevation (m)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>ElevationMode == 0</Visible>
          </Parameter>
          <Parameter>
            <Name>SwellFactor</Name>
            <Text>Balance: fill = cut x factor</Text>
            <Value>1.0</Value>
            <ValueType>Double</ValueType>
            <Visible>ElevationMode == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>CutRatio</Name>
            <Text>Cut slope H:V (e.g. 1.5 = 3/2)</Text>
            <Value>1.5</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.01</MinValue>
          </Parameter>
          <Parameter>
            <Name>FillRatio</Name>
            <Text>Fill slope H:V (e.g. 2 = 2/1)</Text>
            <Value>2.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.01</MinValue>
          </Parameter>
          <Parameter>
            <Name>MaxReach</Name>
            <Text>Max. slope width (m)</Text>
            <Value>50.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.1</MinValue>
          </Parameter>
          <Parameter>
            <Name>GridCell</Name>
            <Text>Computation grid (m, 0 = auto)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0</MinValue>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>POutExp</Name>
        <Text>4. Output</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>PadMesh</Name>
            <Text>Pad surface</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>Outline3D</Name>
            <Text>Pad outline (3D)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>PadProp</Name>
            <Text>Pad format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
          </Parameter>
          <Parameter>
            <Name>SlopeMesh</Name>
            <Text>Slope surfaces</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>CutSlopeProp</Name>
            <Text>Cut slope format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>SlopeMesh == True</Visible>
          </Parameter>
          <Parameter>
            <Name>FillSlopeProp</Name>
            <Text>Fill slope format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>SlopeMesh == True</Visible>
          </Parameter>
          <Parameter>
            <Name>DaylightLine</Name>
            <Text>Daylight line (slope toe / crest)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DaylightProp</Name>
            <Text>Daylight format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>DaylightLine == True</Visible>
          </Parameter>
          <Parameter>
            <Name>DesignMesh</Name>
            <Text>Complete design surface (terrain + platform)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DesignProp</Name>
            <Text>Design surface format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>DesignMesh == True</Visible>
          </Parameter>
          <Parameter>
            <Name>SaveDesign</Name>
            <Text>Save design surface as LandXML</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DesignName</Name>
            <Text>Design name</Text>
            <Value>Platform_design</Value>
            <ValueType>String</ValueType>
            <Visible>SaveDesign == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ResultTexts</Name>
            <Text>Pad elevation text</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>TextHeight</Name>
            <Text>Text height (mm)</Text>
            <Value>2.5</Value>
            <ValueType>Double</ValueType>
          </Parameter>
          <Parameter>
            <Name>MaxFaces</Name>
            <Text>Max. faces per mesh element</Text>
            <Value>30000</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1000</MinValue>
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
            <Value>True</Value>
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
