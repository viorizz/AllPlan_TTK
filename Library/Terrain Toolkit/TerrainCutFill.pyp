<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainCutFill.py</Name>
    <Title>Terrain Cut &amp; Fill (volumes)</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Cut &amp; fill</Text>
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
                <Text>Design surface</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_2</Name>
                <Text>Boundary (optional, closed)</Text>
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
        <Text>2a. Existing terrain source</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>TerrainSource</Name>
            <Text>Existing terrain from</Text>
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
            <Text>Existing terrain file</Text>
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
        <Name>CompareExp</Name>
        <Text>2b. Compare with</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>CompareMode</Name>
            <Text>Compare with</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>CompareMode_0</Name>
                <Text>Design surface</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>CompareMode_1</Name>
                <Text>Reference elevation</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>ReferenceElevation</Name>
            <Text>Reference elevation (m)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <Visible>CompareMode == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>DesignSource</Name>
            <Text>Design surface from</Text>
            <Value>0</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Visible>CompareMode == 0</Visible>
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
            <Text>Design file</Text>
            <Value></Value>
            <ValueType>String</ValueType>
            <ValueDialog>OpenFileDialog</ValueDialog>
            <FileFilter>Terrain files (*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts)|*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts|All files (*.*)|*.*|</FileFilter>
            <FileExtension>xml</FileExtension>
            <Visible>CompareMode == 0 and DesignSource == 1</Visible>
          </Parameter>
          <Parameter>
            <Name>SwellFactor</Name>
            <Text>Swell factor applied to cut</Text>
            <Value>1.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0.1</MinValue>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>MapExp</Name>
        <Text>3. Map &amp; lines</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>HeatMap</Name>
            <Text>Cut/fill depth map</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>DepthBreaks</Name>
            <Text>Depth class limits (m)</Text>
            <Value>-2;-1;-0.5;-0.1;0.1;0.5;1;2</Value>
            <ValueType>String</ValueType>
            <Visible>HeatMap == True</Visible>
          </Parameter>
          <Parameter>
            <Name>MapOnDesign</Name>
            <Text>Draw map at design level</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
            <Visible>HeatMap == True</Visible>
          </Parameter>
          <Parameter>
            <Name>Isopachs</Name>
            <Text>Isopach lines (equal depth)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>IsopachInterval</Name>
            <Text>Isopach interval (m)</Text>
            <Value>0.5</Value>
            <ValueType>Double</ValueType>
            <Visible>Isopachs == True</Visible>
          </Parameter>
          <Parameter>
            <Name>IsopachProp</Name>
            <Text>Isopach format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>Isopachs == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ZeroLineProp</Name>
            <Text>Zero line (cut/fill limit) format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>Isopachs == True</Visible>
          </Parameter>
          <Parameter>
            <Name>ResultTexts</Name>
            <Text>Write volumes as texts in the model</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>ViewExp</Name>
        <Text>4. Output</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>OutputMode</Name>
            <Text>Output</Text>
            <Value>1</Value>
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
          <Parameter>
            <Name>ReportFile</Name>
            <Text>Volume report (CSV, optional)</Text>
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
