<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainMesh.py</Name>
    <Title>Terrain Mesh (TIN)</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Terrain mesh</Text>
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
                <Text>Terrain points / meshes</Text>
                <Value>0</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_1</Name>
                <Text>Breaklines (3D lines)</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_2</Name>
                <Text>Outer boundary (closed)</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SelectRole_3</Name>
                <Text>Holes (closed)</Text>
                <Value>3</Value>
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
        <Text>2. Points from file (optional)</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>TerrainSource</Name>
            <Text>Points from</Text>
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
            <Text>Points file</Text>
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
        <Name>CleanExp</Name>
        <Text>3. Triangulation &amp; cleaning</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>MaxEdge</Name>
            <Text>Max. outer edge length (m, 0 = convex hull)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0</MinValue>
          </Parameter>
          <Parameter>
            <Name>DedupeTol</Name>
            <Text>Merge points closer than (m)</Text>
            <Value>0.001</Value>
            <ValueType>Double</ValueType>
            <MinValue>0</MinValue>
          </Parameter>
          <Parameter>
            <Name>ThinCell</Name>
            <Text>Grid thinning cell (m, 0 = off)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
            <MinValue>0</MinValue>
          </Parameter>
          <Parameter>
            <Name>RemoveSpikes</Name>
            <Text>Remove spikes / outliers</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>SpikeThreshold</Name>
            <Text>Spike threshold (m)</Text>
            <Value>1.0</Value>
            <ValueType>Double</ValueType>
            <Visible>RemoveSpikes == True</Visible>
          </Parameter>
          <Parameter>
            <Name>Simplify</Name>
            <Text>Simplify (keep vertical tolerance)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>SimplifyTol</Name>
            <Text>Vertical tolerance (m)</Text>
            <Value>0.05</Value>
            <ValueType>Double</ValueType>
            <Visible>Simplify == True</Visible>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>OutExp</Name>
        <Text>4. Output</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>CreateMesh</Name>
            <Text>Terrain mesh (polyhedron)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>MeshProp</Name>
            <Text>Mesh format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>CreateMesh == True</Visible>
          </Parameter>
          <Parameter>
            <Name>MaxFaces</Name>
            <Text>Max. faces per mesh element</Text>
            <Value>30000</Value>
            <ValueType>Integer</ValueType>
            <MinValue>1000</MinValue>
          </Parameter>
          <Parameter>
            <Name>CreateOutline</Name>
            <Text>Outline (3D polyline)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>OutlineProp</Name>
            <Text>Outline format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>CreateOutline == True</Visible>
          </Parameter>
          <Parameter>
            <Name>CreateBreaklines</Name>
            <Text>Enforced breaklines (3D)</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>BreaklineProp</Name>
            <Text>Breakline format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>CreateBreaklines == True</Visible>
          </Parameter>
          <Parameter>
            <Name>CreatePoints</Name>
            <Text>Points as 3D crosses</Text>
            <Value>False</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>PointSize</Name>
            <Text>Cross size (m)</Text>
            <Value>0.25</Value>
            <ValueType>Double</ValueType>
            <Visible>CreatePoints == True</Visible>
          </Parameter>
          <Parameter>
            <Name>PointProp</Name>
            <Text>Point format</Text>
            <Value/>
            <ValueType>CommonProperties</ValueType>
            <Visible>CreatePoints == True</Visible>
          </Parameter>
          <Parameter>
            <Name>SaveLandXML</Name>
            <Text>Save a LandXML copy (terrain library)</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>TerrainName</Name>
            <Text>Terrain name</Text>
            <Value>Terrain</Value>
            <ValueType>String</ValueType>
            <Visible>SaveLandXML == True</Visible>
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
