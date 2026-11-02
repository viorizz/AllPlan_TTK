<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>terrain_toolkit\TerrainDiagnostics.py</Name>
    <Title>Terrain Toolkit Diagnostics</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Page1</Name>
    <Text>Diagnostics</Text>
    <Parameters>
      <Parameter>
        <Name>DiagInfoExp</Name>
        <Text>What this does</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>DiagInfo1</Name>
            <Text>1. 'Run self-test' checks the Allplan API and draws a small test terrain</Text>
            <Value></Value>
            <ValueType>Text</ValueType>
          </Parameter>
          <Parameter>
            <Name>DiagInfo2</Name>
            <Text>2. Select elements, then 'Inspect' writes their API details to the log</Text>
            <Value></Value>
            <ValueType>Text</ValueType>
          </Parameter>
          <Parameter>
            <Name>DiagInfo3</Name>
            <Text>3. Send the log file (button 'Open log folder') to the developer</Text>
            <Value></Value>
            <ValueType>Text</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
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
                <Text>Elements to inspect</Text>
                <Value>0</Value>
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
        <Name>TestExp</Name>
        <Text>Self-test</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>CreateTestGeometry</Name>
            <Text>Create test geometry</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>TestRow</Name>
            <Text>Test origin X / Y (m)</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>TestX</Name>
                <Text>X</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
              <Parameter>
                <Name>TestY</Name>
                <Text>Y</Text>
                <Value>0.0</Value>
                <ValueType>Double</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>TestZ</Name>
            <Text>Test origin Z (m)</Text>
            <Value>0.0</Value>
            <ValueType>Double</ValueType>
          </Parameter>
          <Parameter>
            <Name>RunButtonRow</Name>
            <Text>Run self-test</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>RunButton</Name>
                <Text>Run self-test</Text>
                <ValueType>Button</ValueType>
                <EventId>1001</EventId>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>InspectButtonRow</Name>
            <Text>Inspect selected elements</Text>
            <ValueType>Row</ValueType>
            <Parameters>
              <Parameter>
                <Name>InspectButton</Name>
                <Text>Inspect</Text>
                <ValueType>Button</ValueType>
                <EventId>2001</EventId>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>ResultInfo</Name>
            <Text>Last result</Text>
            <Value>-</Value>
            <ValueType>Text</ValueType>
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
